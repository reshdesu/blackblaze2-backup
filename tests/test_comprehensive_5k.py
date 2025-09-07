#!/usr/bin/env python3
"""
Comprehensive 5k Photo Performance Test
Tests deduplication performance with all 5,000 photos
"""

import datetime
import hashlib
import json
import logging
import multiprocessing
import random
import statistics
import time
from pathlib import Path

import pytest
from PIL import Image

from blackblaze_backup.core import BackupManager, CredentialManager

# Set up logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
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


class Comprehensive5kPerformanceTest:
    def __init__(self):
        self.test_dir = Path("test_photos/performance_test")
        self.bucket_name = "blackblaze2-backup-testing"

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

    def upload_sample_photos(self, count=200):
        """Upload a sample of photos to the bucket for realistic testing"""
        print(
            f"Uploading {count} sample photos to bucket for realistic deduplication testing..."
        )

        # Load credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.load_credentials()

        if not credentials:
            print("No credentials found. Please configure the app first.")
            return False

        # Get test files
        test_files = list(self.test_dir.rglob("*.png")) + list(
            self.test_dir.rglob("*.jpg")
        )
        if len(test_files) < count:
            print(f"Not enough test files. Need {count}, found {len(test_files)}")
            return False

        backup_manager = BackupManager()
        s3_client = backup_manager.create_s3_client(credentials)

        # Upload first N files
        uploaded_count = 0
        for i, file_path in enumerate(test_files[:count]):
            try:
                # Create S3 key
                s3_key = f"test-photos/{file_path.name}"

                # Upload file
                success = backup_manager.upload_file(
                    s3_client, file_path, self.bucket_name, s3_key
                )
                if success:
                    uploaded_count += 1

                if (i + 1) % 50 == 0:
                    print(f"   Uploaded {i + 1}/{count} files...")

            except Exception as e:
                print(f"   Failed to upload {file_path.name}: {e}")

        print(f"Successfully uploaded {uploaded_count}/{count} sample photos")
        return uploaded_count > 0

    def test_all_5k_photos(self):
        """Test deduplication performance on all 5,000 photos"""
        print("Comprehensive 5k Photo Performance Test")
        print("=" * 60)

        # Generate 5k test images if they don't exist
        if not self.generate_5k_test_images():
            print("Failed to generate 5k test images")
            return None

        # Get list of all test files
        test_files = list(self.test_dir.rglob("*.png")) + list(
            self.test_dir.rglob("*.jpg")
        )
        print(f"Found {len(test_files):,} test files")

        if len(test_files) < 5000:
            print(f"Not enough test files. Need 5,000, found {len(test_files)}")
            return None

        # Upload sample photos to bucket
        if not self.upload_sample_photos(200):
            print("Failed to upload sample photos. Cannot run realistic test.")
            return None

        # Load credentials
        credential_manager = CredentialManager()
        credentials = credential_manager.load_credentials()

        backup_manager = BackupManager()
        s3_client = backup_manager.create_s3_client(credentials)

        # Reset cache
        backup_manager.reset_cache()

        print(
            f"\nTesting deduplication performance on all {len(test_files):,} photos..."
        )
        print("   This will take approximately 2-3 minutes...")

        # Test cache population
        print("1. Testing cache population...")
        cache_start = time.time()
        backup_manager._populate_hash_cache(s3_client, self.bucket_name)
        cache_time = time.time() - cache_start
        cache_size = len(backup_manager._hash_cache)

        print(f"   Cache populated: {cache_time:.2f}s ({cache_size:,} hashes)")

        # Test file processing on ALL 5k files
        print("2. Testing file processing on all 5,000 photos...")
        processing_times = []
        duplicates_found = 0
        total_start = time.time()

        for i, file_path in enumerate(test_files):
            start_time = time.time()

            # Calculate hash
            file_hash = self.get_file_hash(file_path)

            # Check if exists (this should be fast with cache)
            exists = backup_manager._file_content_exists_in_s3(
                s3_client, self.bucket_name, file_hash
            )

            processing_time = time.time() - start_time
            processing_times.append(processing_time)

            if exists:
                duplicates_found += 1

            # Progress update every 500 files
            if (i + 1) % 500 == 0:
                elapsed = time.time() - total_start
                rate = (i + 1) / elapsed
                eta = (len(test_files) - (i + 1)) / rate if rate > 0 else 0
                avg_time = sum(processing_times) / len(processing_times)
                print(
                    f"   Processed {i + 1:,}/{len(test_files):,} files ({rate:.1f}/sec, ETA: {eta/60:.1f}min, avg: {avg_time*1000:.1f}ms/file)"
                )

        total_time = time.time() - total_start
        avg_processing_time = sum(processing_times) / len(processing_times)

        # Calculate statistics
        min_time = min(processing_times)
        max_time = max(processing_times)
        std_dev = statistics.stdev(processing_times)

        print("\nComprehensive Results:")
        print("=" * 40)
        print(f"Total Files Processed: {len(test_files):,}")
        print(f"Cache Population Time: {cache_time:.3f}s")
        print(f"Cache Size: {cache_size:,} file hashes")
        print(f"Total Processing Time: {total_time:.3f}s")
        print(f"Average Processing per File: {avg_processing_time*1000:.2f}ms")
        print(f"Processing Time Range: {min_time*1000:.2f}ms - {max_time*1000:.2f}ms")
        print(f"Processing Time Std Dev: {std_dev*1000:.2f}ms")
        print(f"Duplicates Found: {duplicates_found:,}")
        print(f"Duplicate Rate: {(duplicates_found/len(test_files)*100):.1f}%")

        # Performance metrics
        files_per_second = len(test_files) / total_time
        estimated_100k_files = (100000 * avg_processing_time) / 60  # minutes

        print("\nPerformance Metrics:")
        print("=" * 30)
        print(f"Files per Second: {files_per_second:.1f}")
        print(f"Estimated 100k Files: {estimated_100k_files:.1f} minutes")
        print(f"Estimated 1M Files: {(estimated_100k_files * 10):.1f} minutes")

        # Save comprehensive results
        self.save_comprehensive_results(
            {
                "total_files": len(test_files),
                "cache_time": cache_time,
                "cache_size": cache_size,
                "total_time": total_time,
                "avg_processing_time": avg_processing_time,
                "min_time": min_time,
                "max_time": max_time,
                "std_dev": std_dev,
                "duplicates_found": duplicates_found,
                "duplicate_rate": duplicates_found / len(test_files) * 100,
                "files_per_second": files_per_second,
                "estimated_100k_minutes": estimated_100k_files,
                "processing_times": processing_times,
            }
        )

        return True

    def save_comprehensive_results(self, results):
        """Save comprehensive results to file"""
        results_file = Path("comprehensive_5k_performance_results.txt")

        with open(results_file, "w") as f:
            f.write("Comprehensive 5k Photo Performance Test Results\n")
            f.write("=" * 60 + "\n\n")

            f.write("Test Configuration:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Files Tested: {results['total_files']:,}\n")
            f.write("Sample Photos in Bucket: 200\n")
            f.write(f"Bucket: {self.bucket_name}\n\n")

            f.write("Performance Results:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Cache Population Time: {results['cache_time']:.3f}s\n")
            f.write(f"Cache Size: {results['cache_size']:,} file hashes\n")
            f.write(f"Total Processing Time: {results['total_time']:.3f}s\n")
            f.write(
                f"Average Processing per File: {results['avg_processing_time']*1000:.2f}ms\n"
            )
            f.write(
                f"Processing Time Range: {results['min_time']*1000:.2f}ms - {results['max_time']*1000:.2f}ms\n"
            )
            f.write(f"Processing Time Std Dev: {results['std_dev']*1000:.2f}ms\n")
            f.write(f"Duplicates Found: {results['duplicates_found']:,}\n")
            f.write(f"Duplicate Rate: {results['duplicate_rate']:.1f}%\n\n")

            f.write("Performance Metrics:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Files per Second: {results['files_per_second']:.1f}\n")
            f.write(
                f"Estimated 100k Files: {results['estimated_100k_minutes']:.1f} minutes\n"
            )
            f.write(
                f"Estimated 1M Files: {(results['estimated_100k_minutes'] * 10):.1f} minutes\n\n"
            )

            f.write("Statistical Analysis:\n")
            f.write("-" * 20 + "\n")
            f.write(
                f"Mean Processing Time: {results['avg_processing_time']*1000:.2f}ms\n"
            )
            f.write(f"Standard Deviation: {results['std_dev']*1000:.2f}ms\n")
            f.write(
                f"95th Percentile: {statistics.quantiles(results['processing_times'], n=20)[18]*1000:.2f}ms\n"
            )
            f.write(
                f"99th Percentile: {statistics.quantiles(results['processing_times'], n=100)[98]*1000:.2f}ms\n"
            )

        print(f"Comprehensive results saved to: {results_file}")

        # Also save JSON format for future reference
        self.save_json_results(results)

    def save_json_results(self, results):
        """Save comprehensive results in JSON format with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create JSON data structure
        json_data = {
            "timestamp": timestamp,
            "test_type": "comprehensive_5k_photos",
            "test_environment": {
                "total_files_tested": results["total_files"],
                "sample_photos_in_bucket": 200,  # Fixed upload count
                "bucket_name": self.bucket_name,
                "deduplication_type": "content-based_hash_checking_with_s3_metadata",
            },
            "performance_results": {
                "cache_population_time": results["cache_time"],
                "cache_size": results["cache_size"],
                "total_processing_time": results["total_time"],
                "average_processing_per_file_ms": results["avg_processing_time"] * 1000,
                "processing_time_range_ms": [
                    min(results["processing_times"]) * 1000,
                    max(results["processing_times"]) * 1000,
                ],
                "processing_time_std_dev_ms": results["std_dev"] * 1000,
                "duplicates_found": results["duplicates_found"],
                "duplicate_rate_percent": results["duplicate_rate"],
                "files_per_second": results["total_files"] / results["total_time"],
            },
            "performance_projections": {
                "estimated_100k_files_minutes": (
                    100000 * results["avg_processing_time"]
                )
                / 60,
                "estimated_1m_files_minutes": (1000000 * results["avg_processing_time"])
                / 60,
                "percentile_95_ms": statistics.quantiles(
                    results["processing_times"], n=20
                )[18]
                * 1000,
                "percentile_99_ms": statistics.quantiles(
                    results["processing_times"], n=100
                )[98]
                * 1000,
            },
            "performance_targets_avg_plus_6sigma": {
                "cache_population_max_seconds": 20.0,
                "processing_per_file_max_ms": 12.0,
                "total_time_max_seconds_500_files": 25.0,
                "cache_lookup_max_ms": 10.0,
            },
            "notes": "Performance targets based on comprehensive testing with 5,000 photos and real S3 connectivity using avg + 6σ methodology",
        }

        # Save to JSON file
        json_file = Path("performance_results.json")
        with open(json_file, "w") as f:
            json.dump(json_data, f, indent=2)

        print(f"JSON results saved to: {json_file}")


@pytest.mark.performance
@pytest.mark.slow
def test_comprehensive_5k_performance():
    """Test deduplication performance on all 5,000 photos"""
    tester = Comprehensive5kPerformanceTest()
    success = tester.test_all_5k_photos()
    assert success, "Comprehensive 5k performance test failed"


def main():
    tester = Comprehensive5kPerformanceTest()
    success = tester.test_all_5k_photos()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
