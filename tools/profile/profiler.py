#!/usr/bin/env python3
"""
Profiling scrip        print("Stockie Performance Profiler")
        print("=" * 40)for stockie performance analysis.
Profiles both load_stock_prices and calculate_indicators with detailed breakdowns.
"""

import cProfile
import pstats
import io
import time
import psutil
import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stockie.loaders.config_loader import ConfigLoader
from stockie.db.database_facade import DatabaseFacade
from stockie.loaders.stock_price_ingestor import StockPriceIngestor
from stockie.indicators.calculate_indicators import CalculateIndicators
from stockie.util.tickers import Tickers
from stockie.log.custom_logger import CustomLogger


class StockieProfiler:
    def __init__(self, config_dir="/prod/stockie/config"):
        self.config_dir = config_dir
        self.results = {}
        
        # Load configuration
        config_loader = ConfigLoader(self.config_dir)
        self.config = config_loader.get()
        
        # Add password to config
        password = os.getenv('STOCKIE_DB_PASSWORD', 'stockie')
        self.config['db']['password'] = password
        
        print("Stockie Performance Profiler")
        print("=" * 50)
    
    def setup_database_connection(self):
        """Create database connection"""
        import psycopg2
        db_config = self.config['db']
        
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password']
        )
        
        return DatabaseFacade(conn)
    
    def profile_load_stock_prices(self, sample_tickers=None, limit=100):
        """Profile the stock price loading process"""
        
        print(f"\nProfiling Load Stock Prices (limit: {limit} tickers)")
        print("-" * 50)        # Setup
        db_facade = self.setup_database_connection()
        
        # Get sample tickers
        if sample_tickers is None:
            logger = CustomLogger('profiler', log_to_console=True, log_level='INFO').get_logger()
            tickers_util = Tickers(logger, self.config)
            all_tickers = tickers_util.all_tickers
            sample_tickers = all_tickers[:limit] if limit else all_tickers
        
        print(f"Profiling with {len(sample_tickers)} tickers: {sample_tickers[:5]}...")
        
        # Create profiler
        profiler = cProfile.Profile()
        
        # Profile the operation
        start_time = time.time()
        start_cpu = psutil.Process().cpu_percent()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        profiler.enable()
        
        try:
            ingestor = StockPriceIngestor(db_facade, self.config)
            ingestor.run(sample_tickers)
        except Exception as e:
            print(f"Error during profiling: {e}")
            return None
        
        profiler.disable()
        
        end_time = time.time()
        end_cpu = psutil.Process().cpu_percent()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Collect stats
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Process profiling results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        profile_output = s.getvalue()
        
        # Store results
        self.results['load_stock_prices'] = {
            'execution_time': execution_time,
            'memory_used_mb': memory_used,
            'tickers_processed': len(sample_tickers),
            'tickers_per_second': len(sample_tickers) / execution_time,
            'profile_stats': profile_output,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"✓ Completed in {execution_time:.2f} seconds")
        print(f"✓ Memory used: {memory_used:.1f} MB")
        print(f"✓ Rate: {len(sample_tickers) / execution_time:.1f} tickers/second")
        
        db_facade.conn.close()
        return self.results['load_stock_prices']
    
    def profile_calculate_indicators(self, sample_tickers=None, limit=100):
        """Profile the indicator calculation process"""
        
        print(f"\nProfiling Calculate Indicators (limit: {limit} tickers)")
        print("-" * 50)        # Setup
        db_facade = self.setup_database_connection()
        
        # Get sample tickers
        if sample_tickers is None:
            logger = CustomLogger('profiler', log_to_console=True, log_level='INFO').get_logger()
            tickers_util = Tickers(logger, self.config)
            all_tickers = tickers_util.all_tickers
            sample_tickers = all_tickers[:limit] if limit else all_tickers
        
        print(f"Profiling with {len(sample_tickers)} tickers: {sample_tickers[:5]}...")
        
        # Create profiler
        profiler = cProfile.Profile()
        
        # Profile the operation
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        profiler.enable()
        
        try:
            calculator = CalculateIndicators(db_facade, self.config)
            calculator.run(sample_tickers)
        except Exception as e:
            print(f"Error during profiling: {e}")
            return None
        
        profiler.disable()
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Collect stats
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        # Process profiling results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(30)  # Top 30 functions
        
        profile_output = s.getvalue()
        
        # Store results
        self.results['calculate_indicators'] = {
            'execution_time': execution_time,
            'memory_used_mb': memory_used,
            'tickers_processed': len(sample_tickers),
            'tickers_per_second': len(sample_tickers) / execution_time,
            'profile_stats': profile_output,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"✓ Completed in {execution_time:.2f} seconds")
        print(f"✓ Memory used: {memory_used:.1f} MB")
        print(f"✓ Rate: {len(sample_tickers) / execution_time:.1f} tickers/second")
        
        db_facade.conn.close()
        return self.results['calculate_indicators']
    
    def profile_individual_indicators(self, sample_tickers=None, limit=50):
        """Profile individual indicator families to identify bottlenecks"""
        
        print(f"\nProfiling Individual Indicators (limit: {limit} tickers)")
        print("-" * 55)
        
        db_facade = self.setup_database_connection()
        
        # Get sample tickers
        if sample_tickers is None:
            logger = CustomLogger('profiler', log_to_console=True, log_level='INFO').get_logger()
            tickers_util = Tickers(logger, self.config)
            all_tickers = tickers_util.all_tickers
            sample_tickers = all_tickers[:limit] if limit else all_tickers
        
        indicator_times = {}
        
        # Test each indicator family individually
        for family, indicators in self.config.get("indicators", {}).items():
            print(f"\nTesting {family} indicators...")
            
            # Create config with only this family
            test_config = self.config.copy()
            test_config["indicators"] = {family: indicators}
            
            start_time = time.time()
            
            try:
                calculator = CalculateIndicators(db_facade, test_config)
                calculator.run(sample_tickers[:10])  # Small sample for individual testing
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                indicator_times[family] = {
                    'time_seconds': execution_time,
                    'time_per_ticker': execution_time / 10,
                    'indicators_count': len(indicators)
                }
                
                print(f"  ✓ {family}: {execution_time:.2f}s ({execution_time/10:.3f}s per ticker)")
                
            except Exception as e:
                print(f"  ✗ {family}: Error - {e}")
                indicator_times[family] = {'error': str(e)}
        
        # Sort by time
        sorted_indicators = sorted(
            [(family, data) for family, data in indicator_times.items() if 'time_seconds' in data],
            key=lambda x: x[1]['time_seconds'],
            reverse=True
        )
        
        print(f"\nIndicator Performance Ranking:")
        print("-" * 40)
        for family, data in sorted_indicators:
            print(f"{family:15} {data['time_seconds']:6.2f}s ({data['time_per_ticker']*1000:5.1f}ms/ticker)")
        
        self.results['individual_indicators'] = indicator_times
        db_facade.conn.close()
        return indicator_times
    
    def save_results(self, filename=None):
        """Save profiling results to files"""
        if filename is None:
            filename = f"profiling_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save detailed profile stats
        for component, data in self.results.items():
            if 'profile_stats' in data:
                with open(f"{filename}_{component}_profile.txt", 'w') as f:
                    f.write(f"Profiling Results for {component}\n")
                    f.write(f"Timestamp: {data['timestamp']}\n")
                    f.write(f"Execution Time: {data['execution_time']:.2f} seconds\n")
                    f.write(f"Memory Used: {data['memory_used_mb']:.1f} MB\n")
                    f.write(f"Tickers Processed: {data['tickers_processed']}\n")
                    f.write(f"Rate: {data['tickers_per_second']:.1f} tickers/second\n")
                    f.write("\n" + "="*80 + "\n")
                    f.write(data['profile_stats'])
        
        # Save summary JSON
        import json
        summary = {}
        for component, data in self.results.items():
            summary[component] = {k: v for k, v in data.items() if k != 'profile_stats'}
        
        with open(f"{filename}_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nResults saved to {filename}_*")
        
    def print_summary(self):
        """Print a summary of profiling results"""
        print(f"\nPROFILING SUMMARY")
        print("=" * 50)
        
        for component, data in self.results.items():
            if 'execution_time' in data:
                print(f"\n{component.upper().replace('_', ' ')}:")
                print(f"  Time: {data['execution_time']:.2f} seconds")
                print(f"  Memory: {data['memory_used_mb']:.1f} MB")
                print(f"  Rate: {data['tickers_per_second']:.1f} tickers/second")
                print(f"  Tickers: {data['tickers_processed']}")


def main():
    """Main profiling function"""
    profiler = StockieProfiler()
    
    print("Select profiling mode:")
    print("1. Load Stock Prices only")
    print("2. Calculate Indicators only") 
    print("3. Individual Indicators breakdown")
    print("4. Full profiling suite")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        profiler.profile_load_stock_prices(limit=100)
    elif choice == "2":
        profiler.profile_calculate_indicators(limit=100)
    elif choice == "3":
        profiler.profile_individual_indicators(limit=50)
    elif choice == "4":
        profiler.profile_load_stock_prices(limit=100)
        profiler.profile_calculate_indicators(limit=100)
        profiler.profile_individual_indicators(limit=50)
    else:
        print("Invalid choice")
        return
    
    profiler.print_summary()
    profiler.save_results()


if __name__ == "__main__":
    main()