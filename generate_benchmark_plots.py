import matplotlib.pyplot as plt
import numpy as np
import json
import os

def load_results():
    if not os.path.exists('benchmark_results.json'):
        print("Error: benchmark_results.json not found. Run run_scalability_tests.py first.")
        return None
        
    with open('benchmark_results.json', 'r') as f:
        return json.load(f)

def create_plots():
    results = load_results()
    if not results:
        return

    # Extract Strong Scalability Data
    strong_data = results['strong_scaling']
    workers = [item['workers'] for item in strong_data]
    strong_speedup = [item['speedup'] for item in strong_data]
    strong_efficiency = [item['efficiency'] for item in strong_data]
    ideal_speedup = workers

    # Extract Weak Scalability Data
    weak_data = results['weak_scaling']
    # weak_workers = [item['workers'] for item in weak_data] # Should match workers
    weak_efficiency = [item['efficiency'] for item in weak_data]

    # 1. Strong Scalability: Speedup
    plt.figure(figsize=(10, 6))
    plt.plot(workers, strong_speedup, 'b-o', linewidth=2, label='Actual Speedup')
    plt.plot(workers, ideal_speedup, 'k--', linewidth=1, label='Ideal Speedup (Linear)')
    plt.xlabel('Number of Workers')
    plt.ylabel('Speedup')
    plt.title('Strong Scalability: Speedup vs Workers')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.savefig('strong_speedup.png', dpi=300)
    print("Generated strong_speedup.png")
    plt.close()

    # 2. Strong Scalability: Efficiency
    plt.figure(figsize=(10, 6))
    plt.plot(workers, strong_efficiency, 'g-o', linewidth=2, label='Efficiency')
    plt.axhline(y=1.0, color='k', linestyle='--', linewidth=1, label='Ideal Efficiency')
    plt.xlabel('Number of Workers')
    plt.ylabel('Efficiency')
    plt.title('Strong Scalability: Efficiency vs Workers')
    plt.ylim(0, max(strong_efficiency) * 1.1)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.savefig('strong_efficiency.png', dpi=300)
    print("Generated strong_efficiency.png")
    plt.close()

    # 3. Weak Scalability: Efficiency
    plt.figure(figsize=(10, 6))
    plt.plot(workers, weak_efficiency, 'r-o', linewidth=2, label='Weak Efficiency')
    plt.axhline(y=1.0, color='k', linestyle='--', linewidth=1, label='Ideal Efficiency')
    plt.xlabel('Number of Workers')
    plt.ylabel('Efficiency')
    plt.title('Weak Scalability: Efficiency vs Workers')
    plt.ylim(0, 1.1)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.savefig('weak_efficiency.png', dpi=300)
    print("Generated weak_efficiency.png")
    plt.close()

    # 4. Strong Scalability: Execution Time
    strong_times = [item['time'] for item in strong_data]
    plt.figure(figsize=(10, 6))
    plt.plot(workers, strong_times, 'm-o', linewidth=2, label='Execution Time')
    plt.xlabel('Number of Workers')
    plt.ylabel('Time (seconds)')
    plt.title('Strong Scalability: Execution Time vs Workers')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.savefig('strong_time.png', dpi=300)
    print("Generated strong_time.png")
    plt.close()

    # 5. Weak Scalability: Execution Time
    weak_times = [item['time'] for item in weak_data]
    plt.figure(figsize=(10, 6))
    plt.plot(workers, weak_times, 'c-o', linewidth=2, label='Execution Time')
    plt.xlabel('Number of Workers')
    plt.ylabel('Time (seconds)')
    plt.title('Weak Scalability: Execution Time vs Workers')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.savefig('weak_time.png', dpi=300)
    print("Generated weak_time.png")
    plt.close()

if __name__ == "__main__":
    create_plots()
