#!/usr/bin/env python3
"""
Comprehensive Performance Test for Deduplication Logic
Tests two approaches with 5k images and establishes performance benchmarks
"""

import hashlib
import logging
import multiprocessing
import random
import time
from pathlib import Path

import pytest
from PIL import Image

from blackblaze_backup.core import BackupManager, CredentialManager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_random_image(args):
    """Generate a single random image - for multiprocessing"""
    file_path, width, height, format_type = args

    # Create random image data
    image_data = []
    for _ in range(width * height):
        # Generate random RGB values
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        image_data.append((r, g, b))

    # Create image
    img = Image.new("RGB", (width, height))
    img.putdata(image_data)

    # Save with specified format
    if format_type == "png":
        img.save(file_path, "PNG")
    else:
        img.save(file_path, "JPEG", quality=random.randint(70, 95))

    return file_path


class PerformanceBenchmark:
    def __init__(self):
        self.test_dir = Path("test_photos/performance_test")

        # Performance benchmarks based on comprehensive 5k photo test with real S3 data (avg + 6σ)
        # Cache: 16.87s for 400 hashes (scales with bucket size)
        # Processing: 1.99ms + 6*1.29ms = 9.73ms
        # Total: 9.952s for 5k files
        self.benchmarks = {
            "cache_population_max": 20.0,  # Max 20s to populate cache (16.87s + buffer for larger buckets)
            "processing_per_file_max": 0.012,  # Max 12ms per file (1.99ms + 6*1.29ms = 9.73ms + buffer)
            "total_time_max": 25.0,  # Max 25s for 500 files (scaled from 5k results + buffer)
            "cache_lookup_max": 0.01,  # Max 10ms per lookup (unchanged)
        }

    def generate_5k_test_images(self):
        """Generate 5,000 test images if they don't exist"""
        print("Checking for 5k test images...")

        # Check if we already have enough images
        existing_files = list(self.test_dir.rglob("*.png")) + list(
            self.test_dir.rglob("*.jpg")
        )
        if len(existing_files) >= 5000:
            print(f"Found {len(existing_files):,} existing test images")
            return True

        print(f"Found {len(existing_files):,} existing images, need 5,000 total")
        print("Generating missing test images...")

        # Create test directory
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        subdirs = [self.test_dir / f"subdir_{i:02d}" for i in range(10)]
        for subdir in subdirs:
            subdir.mkdir(exist_ok=True)

        # Calculate how many images to generate
        images_needed = 5000 - len(existing_files)
        print(f"Generating {images_needed:,} additional images...")

        # Prepare arguments for multiprocessing
        image_args = []
        for i in range(images_needed):
            # Random dimensions
            width = random.randint(400, 1200)
            height = random.randint(300, 900)

            # Random format
            format_type = random.choice(["png", "jpg"])
            extension = "png" if format_type == "png" else "jpg"

            # Random subdirectory
            subdir = random.choice(subdirs)
            file_path = (
                subdir
                / f"image_{i+len(existing_files):06d}_{random.randint(1000, 9999)}.{extension}"
            )

            image_args.append((file_path, width, height, format_type))

        # Generate images using multiprocessing
        print("   Using multiprocessing for faster generation...")
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            # Process in batches to show progress
            batch_size = 500
            for i in range(0, len(image_args), batch_size):
                batch = image_args[i : i + batch_size]
                pool.map(generate_random_image, batch)

                generated = min(i + batch_size, len(image_args))
                print(f"   Generated {generated:,}/{images_needed:,} images...")

        # Verify generation
        final_files = list(self.test_dir.rglob("*.png")) + list(
            self.test_dir.rglob("*.jpg")
        )
        print(f"Successfully generated {len(final_files):,} total test images")

        return len(final_files) >= 5000

    def get_file_hash(self, file_path):
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def approach_1_current_caching(self, test_files):
        """Test current caching approach"""
        print("\nAPPROACH 1: Current Caching System")
        print("=" * 50)

        # Load credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.load_credentials()

        if not credentials:
            print("No credentials found. Please configure the app first.")
            return None

        print(f" Credentials loaded: {list(credentials.keys())}")
        bucket_name = (
            "blackblaze2-backup-testing"  # Use the default bucket name from GUI
        )

        backup_manager = BackupManager()
        s3_client = backup_manager.create_s3_client(credentials)

        # Reset cache
        backup_manager.reset_cache()

        # Test cache population
        print("1. Testing cache population...")
        cache_start = time.time()
        backup_manager._populate_hash_cache(s3_client, bucket_name)
        cache_time = time.time() - cache_start
        cache_size = len(backup_manager._hash_cache)

        print(f"   Cache populated: {cache_time:.2f}s ({cache_size:,} hashes)")

        # Test file processing
        print("2. Testing file processing...")
        processing_times = []
        duplicates_found = 0

        # Test with first 500 files
        test_sample = test_files[:500]

        for i, file_path in enumerate(test_sample):
            start_time = time.time()

            # Calculate hash
            file_hash = self.get_file_hash(file_path)

            # Check if exists (this should be fast with cache)
            exists = backup_manager._file_content_exists_in_s3(
                s3_client, bucket_name, file_hash
            )

            processing_time = time.time() - start_time
            processing_times.append(processing_time)

            if exists:
                duplicates_found += 1

            # Progress update
            if i % 100 == 0 and i > 0:
                avg_time = sum(processing_times) / len(processing_times)
                print(
                    f"    Processed {i:,}/{len(test_sample):,} files (avg: {avg_time*1000:.1f}ms)"
                )

        avg_processing_time = sum(processing_times) / len(processing_times)
        total_time = sum(processing_times)

        print("   Results:")
        print(
            f"      - Average processing time: {avg_processing_time*1000:.2f}ms per file"
        )
        print(
            f"      - Total processing time: {total_time:.2f}s for {len(test_sample):,} files"
        )
        print(f"      - Duplicates found: {duplicates_found}")
        print(
            f"      - Estimated time for 5k files: {(avg_processing_time * 5000)/60:.1f} minutes"
        )

        return {
            "cache_time": cache_time,
            "cache_size": cache_size,
            "avg_processing_time": avg_processing_time,
            "total_time": total_time,
            "duplicates_found": duplicates_found,
            "files_processed": len(test_sample),
        }

    def approach_2_batch_optimization(self, test_files):
        """Test optimized batch processing approach"""
        print("\n APPROACH 2: Batch Optimization")
        print("=" * 50)

        # Load credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.load_credentials()

        if not credentials:
            print("No credentials found. Please configure the app first.")
            return None

        print(f" Credentials loaded: {list(credentials.keys())}")
        bucket_name = (
            "blackblaze2-backup-testing"  # Use the default bucket name from GUI
        )

        backup_manager = BackupManager()
        s3_client = backup_manager.create_s3_client(credentials)

        # Reset cache
        backup_manager.reset_cache()

        # Test batch hash calculation
        print("1. Testing batch hash calculation...")
        batch_start = time.time()

        # Calculate all hashes in batch
        test_sample = test_files[:500]
        file_hashes = {}

        for i, file_path in enumerate(test_sample):
            file_hash = self.get_file_hash(file_path)
            file_hashes[file_path] = file_hash

            if i % 100 == 0 and i > 0:
                print(f"    Calculated {i:,}/{len(test_sample):,} hashes")

        hash_time = time.time() - batch_start
        print(f"     Hash calculation: {hash_time:.2f}s for {len(test_sample):,} files")

        # Test batch S3 lookup
        print("2. Testing batch S3 lookup...")
        lookup_start = time.time()

        # Populate cache once
        backup_manager._populate_hash_cache(s3_client, bucket_name)
        cache_time = time.time() - lookup_start
        cache_size = len(backup_manager._hash_cache)

        print(f"   Cache populated: {cache_time:.2f}s ({cache_size:,} hashes)")

        # Batch lookup all hashes
        lookup_start = time.time()
        duplicates_found = 0

        for _file_path, file_hash in file_hashes.items():
            exists = backup_manager._file_content_exists_in_s3(
                s3_client, bucket_name, file_hash
            )
            if exists:
                duplicates_found += 1

        lookup_time = time.time() - lookup_start

        print(f"    Batch lookup: {lookup_time:.2f}s for {len(test_sample):,} files")
        print("   Results:")
        print(f"      - Hash calculation: {hash_time:.2f}s")
        print(f"      - Cache population: {cache_time:.2f}s")
        print(f"      - Batch lookup: {lookup_time:.2f}s")
        print(f"      - Total time: {hash_time + cache_time + lookup_time:.2f}s")
        print(f"      - Duplicates found: {duplicates_found}")
        print(
            f"      - Estimated time for 5k files: {((hash_time + lookup_time) * 5000/500)/60:.1f} minutes"
        )

        return {
            "hash_time": hash_time,
            "cache_time": cache_time,
            "lookup_time": lookup_time,
            "total_time": hash_time + cache_time + lookup_time,
            "duplicates_found": duplicates_found,
            "files_processed": len(test_sample),
        }

    def evaluate_performance(self, results, approach_name):
        """Evaluate performance against benchmarks"""
        print(f"\n {approach_name} Performance Evaluation")
        print("=" * 50)

        passed = True
        failures = []

        # Check cache population time
        if "cache_time" in results:
            cache_time = results["cache_time"]
            if cache_time > self.benchmarks["cache_population_max"]:
                passed = False
                failures.append(
                    f"Cache population too slow: {cache_time:.2f}s > {self.benchmarks['cache_population_max']}s"
                )
            else:
                print(
                    f" Cache population: {cache_time:.2f}s (benchmark: {self.benchmarks['cache_population_max']}s)"
                )

        # Check processing time per file
        if "avg_processing_time" in results:
            avg_time = results["avg_processing_time"]
            if avg_time > self.benchmarks["processing_per_file_max"]:
                passed = False
                failures.append(
                    f"Processing per file too slow: {avg_time*1000:.2f}ms > {self.benchmarks['processing_per_file_max']*1000}ms"
                )
            else:
                print(
                    f" Processing per file: {avg_time*1000:.2f}ms (benchmark: {self.benchmarks['processing_per_file_max']*1000}ms)"
                )

        # Check total time
        total_time = results["total_time"]
        if total_time > self.benchmarks["total_time_max"]:
            passed = False
            failures.append(
                f"Total time too slow: {total_time:.2f}s > {self.benchmarks['total_time_max']}s"
            )
        else:
            print(
                f" Total time: {total_time:.2f}s (benchmark: {self.benchmarks['total_time_max']}s)"
            )

        # Check lookup time (for approach 2)
        if "lookup_time" in results:
            lookup_time = results["lookup_time"]
            avg_lookup = lookup_time / results["files_processed"]
            if avg_lookup > self.benchmarks["cache_lookup_max"]:
                passed = False
                failures.append(
                    f"Cache lookup too slow: {avg_lookup*1000:.2f}ms > {self.benchmarks['cache_lookup_max']*1000}ms"
                )
            else:
                print(
                    f" Cache lookup: {avg_lookup*1000:.2f}ms (benchmark: {self.benchmarks['cache_lookup_max']*1000}ms)"
                )

        if passed:
            print(" PASSED: All performance benchmarks met!")
        else:
            print(" FAILED: Performance benchmarks not met!")
            for failure in failures:
                print(f"   - {failure}")

        return passed, failures

    def run_comprehensive_test(self):
        """Run the complete performance comparison"""
        print(" 5k Image Performance Test")
        print("=" * 60)

        # Generate 5k test images if they don't exist
        if not self.generate_5k_test_images():
            print(" Failed to generate 5k test images")
            return False

        # Get list of all test files
        test_files = list(self.test_dir.rglob("*.png")) + list(
            self.test_dir.rglob("*.jpg")
        )
        print(f" Found {len(test_files):,} test files")

        if len(test_files) < 500:
            print(" Not enough test files. Need at least 500 files.")
            return False

        # Run both approaches
        results_1 = self.approach_1_current_caching(test_files)
        results_2 = self.approach_2_batch_optimization(test_files)

        # Evaluate performance
        passed_1, failures_1 = self.evaluate_performance(
            results_1, "Approach 1 (Current Caching)"
        )
        passed_2, failures_2 = self.evaluate_performance(
            results_2, "Approach 2 (Batch Optimization)"
        )

        # Compare results
        print("\n PERFORMANCE COMPARISON")
        print("=" * 60)

        if results_1 and results_2:
            print(
                f"{'Metric':<25} {'Approach 1':<15} {'Approach 2':<15} {'Winner':<10}"
            )
            print("-" * 65)

            # Cache population time
            cache_winner = (
                "Approach 2"
                if results_2["cache_time"] < results_1["cache_time"]
                else "Approach 1"
            )
            print(
                f"{'Cache Population':<25} {results_1['cache_time']:.2f}s{'':<8} {results_2['cache_time']:.2f}s{'':<8} {cache_winner:<10}"
            )

            # Processing time per file
            if "avg_processing_time" in results_1:
                proc_time_1 = results_1["avg_processing_time"] * 1000  # Convert to ms
                proc_time_2 = (
                    results_2["lookup_time"] / results_2["files_processed"] * 1000
                )
                proc_winner = (
                    "Approach 2" if proc_time_2 < proc_time_1 else "Approach 1"
                )
                print(
                    f"{'Processing per file':<25} {proc_time_1:.2f}ms{'':<6} {proc_time_2:.2f}ms{'':<6} {proc_winner:<10}"
                )

            # Total time
            total_winner = (
                "Approach 2"
                if results_2["total_time"] < results_1["total_time"]
                else "Approach 1"
            )
            print(
                f"{'Total Time':<25} {results_1['total_time']:.2f}s{'':<8} {results_2['total_time']:.2f}s{'':<8} {total_winner:<10}"
            )

            # Duplicates found
            print(
                f"{'Duplicates Found':<25} {results_1['duplicates_found']:<15} {results_2['duplicates_found']:<15} {'Same':<10}"
            )

            # Estimated time for 5k files
            if "avg_processing_time" in results_1:
                est_time_1 = (results_1["avg_processing_time"] * 5000) / 60
                est_time_2 = (
                    (results_2["lookup_time"] / results_2["files_processed"]) * 5000
                ) / 60
                est_winner = "Approach 2" if est_time_2 < est_time_1 else "Approach 1"
                print(
                    f"{'Est. 5k files time':<25} {est_time_1:.1f}min{'':<8} {est_time_2:.1f}min{'':<8} {est_winner:<10}"
                )

            print("\n RECOMMENDATION:")
            if results_2["total_time"] < results_1["total_time"]:
                print("   Approach 2 (Batch Optimization) is faster!")
                print("   - Better for large-scale backups")
                print("   - More efficient memory usage")
                print("   - Better scalability")
            else:
                print("   Approach 1 (Current Caching) is faster!")
                print("   - Simpler implementation")
                print("   - Good for moderate file counts")
                print("   - Easier to maintain")

        # Overall test result
        overall_passed = passed_1 or passed_2
        print(f"\n OVERALL TEST RESULT: {'PASSED' if overall_passed else 'FAILED'}")

        if not overall_passed:
            print(" Both approaches failed performance benchmarks!")
            print("   Consider optimizing the deduplication logic.")

        return overall_passed


@pytest.mark.performance
@pytest.mark.slow
def test_deduplication_performance():
    """Test deduplication performance with 5k images"""
    benchmark = PerformanceBenchmark()
    success = benchmark.run_comprehensive_test()
    assert success, "Performance benchmarks not met"


def main():
    benchmark = PerformanceBenchmark()
    success = benchmark.run_comprehensive_test()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
