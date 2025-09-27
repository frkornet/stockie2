import argparse
import os
import yaml
import time
import psycopg2
from glob import glob
from dotenv import load_dotenv
from multiprocessing import Process
from stockie.log.custom_logger import CustomLogger
from stockie.db.database_utilities import DatabaseUtilities
from stockie.loaders.config_loader import ConfigLoader

def load_file_batch(file_list, log_path):
    start_batch = time.time()

    logger = CustomLogger(
        log_dir=os.path.dirname(log_path),
        log_filename=os.path.basename(log_path)
    ).get_logger()

    load_dotenv()

    try:
        conn = psycopg2.connect(dbname="stockie_db", user="stockie", password=os.getenv('DB_PASSWORD'))
        db_util = DatabaseUtilities(conn)

        for file_path in file_list:
            logger.info(f"Loading file: {file_path}")
            start_file = time.time()
            try:
                db_util.copy_from_file(file_path)
                duration_file = (time.time() - start_file)/60
                logger.info(f"Successfully loaded: {file_path} in {duration_file:.2f} minutes")
            except Exception as e:
                duration_file = time.time() - start_file
                logger.exception("Stack trace:")
                logger.error(f"Error loading {file_path} after {duration_file:.2f} seconds: {e}")

        conn.close()
    except Exception as e:
        logger.exception(f"Database connection failed: {e}")

    duration_batch = (time.time() - start_batch)/60
    logger.info(f"Batch completed in {duration_batch:.2f} minutes with {len(file_list)} file(s)")

def load_technical_indicators(config_dir):
    start = time.time()

    # Load settings from YAML
    config_loader = ConfigLoader(
        config_path=os.path.join(config_dir, "settings.yaml"),
        dotenv_path=os.path.join(config_dir, ".env")
    )
    config = config_loader.get()["load_indicators"]

    process_count = config["load_processes"]
    csv_dir = config["cvs_directory"]
    log_path, log_level, log_to_console = config["log_filename"], config["log_level"], config['console']

    logger = CustomLogger(
        name=__file__,
        log_to_console=log_to_console,
        log_level=log_level,
        log_dir=os.path.dirname(log_path),
        log_filename=os.path.basename(log_path)
    ).get_logger()
    logger.info(f'\n\n *** Starting load technical indicators job.')

    # Discover CSV files
    file_list = sorted(glob(os.path.join(csv_dir, "indicators_part*.csv")))
    total_files = len(file_list)

    if total_files == 0:
        logger.warning("No CSV files found for ingestion.")
        return

    # Adjust process count based on file count
    process_count = min(process_count, total_files)

    # Distribute files across processes
    batches = [[] for _ in range(process_count)]
    for i, file_path in enumerate(file_list):
        batches[i % process_count].append(file_path)

    # Truncate table before ingestion
    try:
        load_dotenv(os.path.join(config_dir, ".env"))
        conn = psycopg2.connect(dbname="stockie_db", user="stockie", password=os.getenv('DB_PASSWORD'))
        db_util = DatabaseUtilities(conn)
        db_util.truncate_table("technical_indicators")
        logger.info("Truncated technical_indicators table.")
        conn.close()
    except Exception as e:
        logger.exception(f"Failed to truncate table: {e}")
        return

    # Launch parallel ingestion processes
    processes = []
    for batch in batches:
        p = Process(target=load_file_batch, args=(batch, log_path))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    duration = (time.time() - start)/60
    logger.info(f"All ingestion processes completed in {duration:.2f} minutes.")
    logger.info(f'*** Finished load technical indicators job.')

def main():
    parser = argparse.ArgumentParser(description="Load technical indicators from CSV files.")
    parser.add_argument("--config-dir", default="/mnt/repos/stockie/config/", help="Directory containing settings.yaml and .env")
    args = parser.parse_args()
    load_technical_indicators(args.config_dir)

if __name__ == '__main__':
    main()