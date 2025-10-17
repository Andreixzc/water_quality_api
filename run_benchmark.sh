#!/bin/bash

# Parallel Processing Benchmark Runner
# Runs the benchmark inside the Docker container

echo "=========================================="
echo "Running Parallel Processing Benchmark"
echo "=========================================="
echo ""
echo "This will test:"
echo "  1. Strong Scalability (fixed problem, varying workers)"
echo "  2. Weak Scalability (proportional problem size with workers)"
echo ""
echo "Results will be saved to: benchmark_results/"
echo ""

# Install required packages if not present
echo "Installing required Python packages..."
sudo docker-compose exec web pip install matplotlib pandas seaborn

# Run the benchmark
echo ""
echo "Starting benchmark (this may take several minutes)..."
sudo docker-compose exec web python benchmark_parallel.py

# Copy results from container to host
echo ""
echo "Copying results from container..."
sudo docker cp water_quality_api-web-1:/app/benchmark_results ./benchmark_results

echo ""
echo "=========================================="
echo "Benchmark Complete!"
echo "=========================================="
echo ""
echo "Results available in: ./benchmark_results/"
echo "  - strong_scalability_results.csv"
echo "  - weak_scalability_results.csv"
echo "  - strong_scalability.png"
echo "  - weak_scalability.png"
echo "  - BENCHMARK_REPORT.md"
