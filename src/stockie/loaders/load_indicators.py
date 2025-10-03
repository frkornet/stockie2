import argparse
import os
import yaml
import time
import psycopg2
from glob import glob
from dotenv import load_dotenv
from multiprocessing import Process
from stockie.log.custom_logger import CustomLogger
from stockie.db.database_facade import DatabaseFacade
from stockie.loaders.config_loader import ConfigLoader

def load_file_batch(file_list, log_path, db_config):
    start_batch = time.time()

    logger = CustomLogger(
        log_dir=os.path.dirname(log_path),
        log_filename=os.path.basename(log_path)
    ).get_logger()

    load_dotenv()

    try:
        conn = psycopg2.connect(**db_config)
        db_facade = DatabaseFacade(conn)

        for file_path in file_list:
            logger.info(f"Loading file: {file_path}")
            start_file = time.time()
            try:
                db_facade.copy_from_file(file_path)
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

def load_technical_indicators(db_facade, full_config: dict) -> None:
    """
    Load technical indicators using the provided database facade and configuration.
    
    Args:
        db_facade: DatabaseFacade instance to use
        full_config: Full configuration dictionary
    """
    start = time.time()

    indicator_config = full_config['load_indicators']

    logger = CustomLogger(
        name=__file__,
        log_to_console=indicator_config['console'],
        log_level=indicator_config['log_level'],
        log_dir=os.path.dirname(indicator_config['log_filename']),
        log_filename=os.path.basename(indicator_config['log_filename'])
    ).get_logger()
    logger.info(f'\n\n *** Starting load technical indicators job.')

    # Discover CSV files
    csv_dir = indicator_config["csv_directory"]
    file_list = sorted(glob(os.path.join(csv_dir, "indicators_part*.csv")))
    total_files = len(file_list)

    if total_files == 0:
        logger.warning("No CSV files found for ingestion.")
        return

    # Adjust process count based on file count
    process_count = indicator_config["load_processes"]
    process_count = min(process_count, total_files)

    # Distribute files across processes
    batches = [[] for _ in range(process_count)]
    for i, file_path in enumerate(file_list):
        batches[i % process_count].append(file_path)

    # Truncate table before ingestion
    try:
        db_facade.truncate_table("technical_indicators")
        logger.info("Truncated technical_indicators table.")
    except Exception as e:
        logger.exception(f"Failed to truncate table: {e}")
        return

    # Launch parallel ingestion processes
    processes = []
    for batch in batches:
        p = Process(target=load_file_batch, args=(batch, indicator_config['log_filename'], full_config['db']))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    duration = (time.time() - start)/60
    logger.info(f"All ingestion processes completed in {duration:.2f} minutes.")
    logger.info(f'*** Finished load technical indicators job.')
