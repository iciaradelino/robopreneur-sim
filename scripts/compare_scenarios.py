# comparison script for experiment scenarios
# usage: python scripts/compare_scenarios.py <experiment_folder>

import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def load_experiment_summaries(exp_folder):
    """load summary data from all scenarios in an experiment"""
    exp_path = Path(exp_folder)
    
    scenarios = ['scenario-a', 'scenario-b', 'scenario-c']
    summaries = {}
    
    for scenario in scenarios:
        summary_path = exp_path / scenario / 'summary.csv'
        if summary_path.exists():
            df = pd.read_csv(summary_path)
            summaries[scenario] = df.iloc[0].to_dict()
        else:
            print(f"warning: {summary_path} not found")
    
    return summaries

def create_comparison_table(summaries):
    """create comparison table from summaries"""
    df = pd.DataFrame(summaries).T
    df.index.name = 'scenario'
    return df

def plot_comparison(df, exp_folder):
    """generate comparison plots"""
    exp_path = Path(exp_folder)
    output_dir = exp_path / 'comparison'
    output_dir.mkdir(exist_ok=True)
    
    # metrics to compare
    metrics = [
        ('final_gini', 'final gini coefficient'),
        ('final_system_wealth', 'final system wealth'),
        ('total_tasks_completed', 'total tasks completed'),
        ('avg_queue_size', 'average queue size'),
        ('max_queue_size', 'max queue size'),
        ('avg_critical_battery_rate', 'avg critical battery rate'),
    ]
    
    # create bar plots for each metric
    for metric_key, metric_label in metrics:
        if metric_key in df.columns:
            fig, ax = plt.subplots(figsize=(8, 5))
            
            scenarios = df.index.tolist()
            values = df[metric_key].values
            
            bars = ax.bar(scenarios, values, color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.8)
            ax.set_ylabel(metric_label)
            ax.set_title(f'comparison: {metric_label}')
            ax.grid(axis='y', alpha=0.3)
            
            # add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.2f}',
                       ha='center', va='bottom')
            
            plt.tight_layout()
            filename = f'comparison_{metric_key}.png'
            plt.savefig(output_dir / filename, dpi=300)
            plt.close()
            print(f"  saved: {filename}")

def generate_comparison_report(df, exp_folder):
    """generate markdown comparison report"""
    exp_path = Path(exp_folder)
    output_dir = exp_path / 'comparison'
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / 'COMPARISON_REPORT.md'
    
    with open(report_path, 'w') as f:
        f.write(f"# scenario comparison: {exp_path.name}\n\n")
        f.write("## summary statistics\n\n")
        
        # write table
        f.write(df.to_markdown())
        f.write("\n\n")
        
        # key observations
        f.write("## key observations\n\n")
        
        if 'final_gini' in df.columns:
            gini_trend = df['final_gini'].values
            f.write(f"- **gini coefficient**: {gini_trend[0]:.3f} → {gini_trend[1]:.3f} → {gini_trend[2]:.3f}\n")
        
        if 'final_system_wealth' in df.columns:
            wealth_trend = df['final_system_wealth'].values
            f.write(f"- **system wealth**: {wealth_trend[0]:.1f} → {wealth_trend[1]:.1f} → {wealth_trend[2]:.1f}\n")
        
        if 'total_tasks_completed' in df.columns:
            tasks_trend = df['total_tasks_completed'].values
            f.write(f"- **tasks completed**: {tasks_trend[0]:.0f} → {tasks_trend[1]:.0f} → {tasks_trend[2]:.0f}\n")
        
        if 'avg_queue_size' in df.columns:
            queue_trend = df['avg_queue_size'].values
            f.write(f"- **avg queue size**: {queue_trend[0]:.2f} → {queue_trend[1]:.2f} → {queue_trend[2]:.2f}\n")
        
        if 'avg_critical_battery_rate' in df.columns:
            battery_trend = df['avg_critical_battery_rate'].values
            f.write(f"- **critical battery rate**: {battery_trend[0]:.3f} → {battery_trend[1]:.3f} → {battery_trend[2]:.3f}\n")
        
        f.write("\n## plots\n\n")
        f.write("see comparison plots in this folder:\n")
        f.write("- comparison_final_gini.png\n")
        f.write("- comparison_final_system_wealth.png\n")
        f.write("- comparison_total_tasks_completed.png\n")
        f.write("- comparison_avg_queue_size.png\n")
        f.write("- comparison_max_queue_size.png\n")
        f.write("- comparison_avg_critical_battery_rate.png\n")
    
    print(f"  saved: COMPARISON_REPORT.md")

def main(exp_folder):
    """main comparison workflow"""
    print(f"\ncomparing scenarios in: {exp_folder}\n")
    
    # load data
    print("loading scenario summaries...")
    summaries = load_experiment_summaries(exp_folder)
    
    if not summaries:
        print("error: no summary files found")
        sys.exit(1)
    
    print(f"  loaded {len(summaries)} scenarios\n")
    
    # create comparison table
    df = create_comparison_table(summaries)
    print("comparison table:")
    print(df)
    print()
    
    # generate plots
    print("generating comparison plots...")
    plot_comparison(df, exp_folder)
    print()
    
    # generate report
    print("generating comparison report...")
    generate_comparison_report(df, exp_folder)
    
    exp_path = Path(exp_folder)
    output_dir = exp_path / 'comparison'
    print(f"\nall comparison results saved to: {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/compare_scenarios.py <experiment_folder>")
        print("\nexample:")
        print("  python scripts/compare_scenarios.py experiments/exp-01-battery")
        sys.exit(1)
    
    exp_folder = sys.argv[1]
    
    if not Path(exp_folder).exists():
        print(f"error: folder not found: {exp_folder}")
        sys.exit(1)
    
    main(exp_folder)
