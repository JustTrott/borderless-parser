# this is just for fun lol
import time
from typing import Dict, Any, List
import statistics
from parser import fetch_full_stories
import multiprocessing

def run_benchmark(
    story_count: int,
    parallel: bool,
    max_workers: int,
    runs: int = 3
) -> Dict[str, Any]:
    """
    Run benchmark for story fetching with given parameters.
    
    Args:
        story_count: Number of stories to fetch
        parallel: Whether to use parallel processing
        max_workers: Number of worker threads
        runs: Number of times to run the test
    
    Returns:
        Dictionary with benchmark results
    """
    times: List[float] = []
    story_counts: List[int] = []
    
    for i in range(runs):
        print(f"  Run {i + 1}/{runs}")
        start_time = time.time()
        
        stories = fetch_full_stories(
            count=story_count,
            parallel=parallel,
            max_workers=max_workers
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        times.append(duration)
        story_counts.append(len(stories))
        
        # Sleep between runs to avoid rate limiting
        time.sleep(2)
    
    return {
        "config": {
            "story_count": story_count,
            "parallel": parallel,
            "max_workers": max_workers,
            "runs": runs
        },
        "results": {
            "mean_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "avg_stories": statistics.mean(story_counts),
            "stories_per_second": statistics.mean(story_counts) / statistics.mean(times)
        }
    }

def print_benchmark_results(results: Dict[str, Any]) -> None:
    """Pretty print benchmark results."""
    config = results["config"]
    stats = results["results"]
    
    print("\nBenchmark Results:")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Stories requested: {config['story_count']}")
    print(f"  Parallel: {config['parallel']}")
    print(f"  Max workers: {config['max_workers']}")
    print(f"  Number of runs: {config['runs']}")
    print("\nResults:")
    print(f"  Mean time: {stats['mean_time']:.2f}s")
    print(f"  Median time: {stats['median_time']:.2f}s")
    print(f"  Min time: {stats['min_time']:.2f}s")
    print(f"  Max time: {stats['max_time']:.2f}s")
    print(f"  Std deviation: {stats['std_dev']:.2f}s")
    print(f"  Avg stories fetched: {stats['avg_stories']:.1f}")
    print(f"  Stories per second: {stats['stories_per_second']:.2f}")
    print("=" * 60)

def main():
    """Run benchmarks with different configurations."""
    cpu_count = multiprocessing.cpu_count()
    print(f"CPU cores available: {cpu_count}")
    
    # Test configurations for 50 stories
    configs = [
        # Sequential baseline
        {"story_count": 50, "parallel": False, "max_workers": 1},
        
        # Parallel processing with different worker counts
        {"story_count": 50, "parallel": True, "max_workers": 2},
        {"story_count": 50, "parallel": True, "max_workers": 5},
        {"story_count": 50, "parallel": True, "max_workers": 10},
    ]
    
    # Previous test configurations (commented out)
    """
    configs = [
        {"story_count": 10, "parallel": False, "max_workers": 1},
        {"story_count": 10, "parallel": True, "max_workers": 2},
        {"story_count": 10, "parallel": True, "max_workers": 3},
        {"story_count": 10, "parallel": True, "max_workers": 5},
        {"story_count": 20, "parallel": True, "max_workers": 3},
    ]
    """
    
    all_results = []
    
    print("\nStarting benchmarks...")
    print("This may take a while, testing 50 stories with different worker counts...")
    
    for config in configs:
        print(f"\nRunning benchmark with config: {config}")
        results = run_benchmark(**config)
        all_results.append(results)
        print_benchmark_results(results)
    
    # Compare results
    print("\nPerformance Summary:")
    print("-" * 80)
    print(f"{'Config':12} | {'Workers':8} | {'Mean Time':10} | {'Stories/Sec':11} | {'Speedup':8}")
    print("-" * 80)
    
    # Get baseline (sequential) performance
    baseline_speed = next(r["results"]["stories_per_second"] for r in all_results if not r["config"]["parallel"])
    
    for result in all_results:
        config = result["config"]
        stats = result["results"]
        speedup = stats["stories_per_second"] / baseline_speed
        
        config_str = f"{'P' if config['parallel'] else 'S'}-{config['story_count']:02d}"
        print(f"{config_str:12} | {config['max_workers']:8d} | {stats['mean_time']:10.2f} | "
              f"{stats['stories_per_second']:11.2f} | {speedup:8.2f}x")

if __name__ == "__main__":
    main()
