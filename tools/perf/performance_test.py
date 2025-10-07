#!/usr/bin/env python3
"""
Performance testing script for calculate_indicators optimization.
Tests different combinations of db_batch_size and process counts.
"""

import os
import sys
import time
import yaml
import shutil
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add src to path to import modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stockie.loaders.config_loader import ConfigLoader
from stockie.db.database_facade import DatabaseFacade


class PerformanceTester:
    def __init__(self, config_dir="/prod/stockie/config", use_all_db_tickers=True):
        self.config_dir = config_dir
        self.use_all_db_tickers = use_all_db_tickers  # Option to use all DB tickers vs config tickers
        self.results = []
        
        # Test parameters
        self.batch_sizes = [100, 200, 300, 400, 500]
        self.process_counts = [8, 9, 10, 11, 12]
    
    def _run_calculate_indicators_test(self, batch_size, process_count):
        """Run a single calculate_indicators test and return execution time"""
        start_time = time.time()
        
        try:
            # Load prod config
            config_loader = ConfigLoader(self.config_dir)
            config = config_loader.get()
            
            # Override the parameters we're testing (don't modify file)
            config['calculate_indicators']['db_batch_size'] = batch_size
            config['calculate_indicators']['calculate_processes'] = process_count
            
            # Add password to config for multiprocessing
            password = os.getenv('STOCKIE_DB_PASSWORD', 'stockie')
            config['db']['password'] = password
            
            # Connect to database for getting tickers
            db_config = config['db']
            import psycopg2
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['dbname'],
                user=db_config['user'],
                password=password
            )
            
            db_facade = DatabaseFacade(conn)
            
            # Get list of tickers 
            if self.use_all_db_tickers:
                # Use ALL tickers from database for max load testing
                all_tickers = db_facade.get_unique_tickers()
                print(f"Using ALL database tickers for maximum load testing")
            else:
                # Use configured tickers only (more realistic for prod config)
                from stockie.util.tickers import Tickers
                from stockie.log.custom_logger import CustomLogger
                
                # Create logger for tickers
                logger = CustomLogger(
                    name="performance_test",
                    log_to_console=True,
                    log_level="INFO"
                ).get_logger()
                
                tickers_util = Tickers(logger, config)
                all_tickers = tickers_util.all_tickers  # Property access, not method call
                print(f"Using configured tickers per prod settings")
            
            print(f"Testing with {len(all_tickers)} tickers...")
            
            # Close the connection before multiprocessing (each process will create its own)
            conn.close()
            
            # Run calculate_indicators with multiprocessing using our specific tickers
            self._run_multiprocess_calculation(all_tickers, config)
            
        except Exception as e:
            print(f"ERROR during test: {e}")
            print("Full stack trace:")
            traceback.print_exc()
            return None
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return execution_time
    
    def _run_multiprocess_calculation(self, tickers, config):
        """Run calculate_indicators with multiprocessing using specific tickers"""
        from stockie.indicators.calculate_indicators import worker
        import multiprocessing
        
        # Get process count from config
        n_processes = config['calculate_indicators']['calculate_processes']
        
        print(f"Starting calculation with {len(tickers)} tickers using {n_processes} processes")
        
        if n_processes > 1:
            # Split tickers into chunks
            chunks = self._chunk_list(tickers, n_processes)
            benchmarks = config.get("tickers", {}).get("benchmarks", [])
            
            print(f"Split into {len(chunks)} chunks:")
            for i, chunk in enumerate(chunks):
                print(f"  Process {i}: {len(chunk)} tickers before adding benchmarks")
            
            process_list = []
            for i, chunk in enumerate(chunks):
                # Add benchmarks to each chunk (like the original code)
                chunk_with_benchmarks = sorted(list(set(chunk + benchmarks)))
                print(f"  Process {i}: {len(chunk_with_benchmarks)} tickers after adding benchmarks")
                p = multiprocessing.Process(target=worker, args=(chunk_with_benchmarks, config, i))
                p.start()
                process_list.append(p)
            
            # Wait for all processes to complete
            for p in process_list:
                p.join()
        else:
            # Single process mode - create new connection like worker does
            import psycopg2
            from stockie.indicators.calculate_indicators import CalculateIndicators
            from stockie.db.database_facade import DatabaseFacade
            
            db_conn = psycopg2.connect(**config["db"])
            db_facade = DatabaseFacade(db_conn)
            calculator = CalculateIndicators(db_facade, config)
            calculator.run(tickers)
            db_conn.close()
    
    def _chunk_list(self, lst, n):
        """Split a list into n roughly equal chunks"""
        k, m = divmod(len(lst), n)
        return [lst[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]
    
    def run_single_test(self, batch_size, process_count):
        """Run a single test configuration"""
        start_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*60}")
        print(f"Testing: batch_size={batch_size}, processes={process_count}")
        print(f"Started at: {start_timestamp}")
        print(f"{'='*60}")
        
        # Run test (parameters passed directly, no config file changes)
        execution_time = self._run_calculate_indicators_test(batch_size, process_count)
        
        if execution_time is not None:
            result = {
                'batch_size': batch_size,
                'processes': process_count,
                'execution_time_seconds': round(execution_time, 2),
                'execution_time_minutes': round(execution_time / 60, 2),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'test_order': len(self.results) + 1  # Track test order for thermal analysis
            }
            
            self.results.append(result)
            
            print(f"✓ Completed in {execution_time:.2f} seconds ({execution_time/60:.2f} minutes)")
            return result
        else:
            print("✗ Test failed")
            return None
    
    def run_all_tests(self):
        """Run all test combinations"""
        print("Starting performance testing...")
        print(f"Testing {len(self.batch_sizes)} batch sizes × {len(self.process_counts)} process counts = {len(self.batch_sizes) * len(self.process_counts)} combinations")
        
        total_tests = len(self.batch_sizes) * len(self.process_counts)
        current_test = 0
        
        for batch_size in self.batch_sizes:
            for process_count in self.process_counts:
                current_test += 1
                print(f"\nProgress: {current_test}/{total_tests}")
                
                result = self.run_single_test(batch_size, process_count)
                
                if result:
                    # Print intermediate results
                    self._print_current_best()
                
                # Longer cooling break between tests to prevent thermal throttling
                print(f"Cooling break: waiting 60 seconds before next test...")
                time.sleep(60)
    
    def _print_current_best(self):
        """Print current best result"""
        if not self.results:
            return
        
        best = min(self.results, key=lambda x: x['execution_time_seconds'])
        print(f"\nCurrent best: batch_size={best['batch_size']}, processes={best['processes']}, time={best['execution_time_minutes']:.2f} min")
    
    def save_results(self, filename="performance_test_results.csv"):
        """Save results to CSV file"""
        if not self.results:
            print("No results to save")
            return
        
        df = pd.DataFrame(self.results)
        df.to_csv(filename, index=False)
        print(f"✓ Results saved to {filename}")
    
    def print_summary(self):
        """Print summary of all results"""
        if not self.results:
            print("No results to summarize")
            return
        
        print(f"\n{'='*80}")
        print("PERFORMANCE TEST SUMMARY")
        print(f"{'='*80}")
        
        df = pd.DataFrame(self.results)
        
        # Sort by execution time
        df_sorted = df.sort_values('execution_time_seconds')
        
        print("\nTop 5 Best Configurations:")
        print("-" * 70)
        print(f"{'Rank':<5} {'Batch Size':<12} {'Processes':<10} {'Time (min)':<12} {'Time (sec)':<12}")
        print("-" * 70)
        
        for i, (_, row) in enumerate(df_sorted.head().iterrows(), 1):
            print(f"{i:<5} {row['batch_size']:<12} {row['processes']:<10} {row['execution_time_minutes']:<12.2f} {row['execution_time_seconds']:<12.2f}")
        
        print("\nAll Results:")
        print("-" * 70)
        print(df_sorted.to_string(index=False))
        
        # Best configuration
        best = df_sorted.iloc[0]
        print(f"\n🏆 BEST CONFIGURATION:")
        print(f"   Batch Size: {best['batch_size']}")
        print(f"   Processes: {best['processes']}")
        print(f"   Time: {best['execution_time_minutes']:.2f} minutes ({best['execution_time_seconds']:.2f} seconds)")
        
        # Performance analysis
        print(f"\nANALYSIS:")
        fastest_time = df_sorted.iloc[0]['execution_time_seconds']
        slowest_time = df_sorted.iloc[-1]['execution_time_seconds']
        improvement = ((slowest_time - fastest_time) / slowest_time) * 100
        
        print(f"   Best time: {fastest_time:.2f} seconds")
        print(f"   Worst time: {slowest_time:.2f} seconds")
        print(f"   Performance range: {improvement:.1f}% improvement from worst to best")
        
        # Check for thermal throttling patterns
        if len(df_sorted) > 5:
            early_tests = df_sorted[df_sorted['test_order'] <= 5]['execution_time_seconds'].mean()
            late_tests = df_sorted[df_sorted['test_order'] > 5]['execution_time_seconds'].mean()
            thermal_impact = ((late_tests - early_tests) / early_tests) * 100
            
            print(f"\n🌡️  THERMAL ANALYSIS:")
            print(f"   Early tests avg: {early_tests:.2f} seconds")
            print(f"   Later tests avg: {late_tests:.2f} seconds")
            if thermal_impact > 5:
                print(f"   WARNING: Possible thermal throttling: {thermal_impact:.1f}% slower in later tests")
            else:
                print(f"   No significant thermal impact: {thermal_impact:.1f}% difference")
    
    def cleanup(self):
        """Clean up (no config restoration needed since we don't modify files)"""
        print("No cleanup needed - config files unchanged")


def main():
    """Main function to run performance tests"""
    print("Calculate Indicators Performance Testing (Production)")
    print("=" * 60)
    
    # Option 1: Test with configured tickers (~500-2000 depending on config)
    # tester = PerformanceTester()
    
    # Option 2: Test with ALL database tickers (~8000+ for maximum load)
    tester = PerformanceTester(use_all_db_tickers=True)
    
    try:
        # Run all tests
        tester.run_all_tests()
        
        # Save and display results
        tester.save_results("calculate_indicators_performance_results.csv")
        tester.print_summary()
        
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
    except Exception as e:
        print(f"\n\nError during testing: {e}")
    finally:
        # Clean up
        tester.cleanup()
        print("\nTesting completed")


if __name__ == "__main__":
    main()