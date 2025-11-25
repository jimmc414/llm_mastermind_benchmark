"""Report generator for Mastermind LLM Benchmark results."""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from glob import glob
from typing import Optional
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from tabulate import tabulate

# Use non-interactive backend for matplotlib
matplotlib.use('Agg')


def load_results(input_patterns: list[str], filter_model: Optional[str] = None,
                 filter_outcome: Optional[str] = None) -> pd.DataFrame:
    """
    Load results from JSONL files and return as DataFrame.

    Args:
        input_patterns: List of glob patterns for input files
        filter_model: Optional model name filter
        filter_outcome: Optional outcome filter (win/loss/error)

    Returns:
        DataFrame with flattened result records
    """
    records = []

    for pattern in input_patterns:
        files = glob(pattern)
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        result = json.loads(line)

                        # Flatten result for DataFrame
                        record = {
                            'file': Path(file_path).name,
                            'model': result['llm_config']['model'],
                            'mode': result['llm_config']['mode'],
                            'outcome': result['outcome'],
                            'total_turns': result['total_turns'],
                            'duration_seconds': result['duration_seconds'],
                            'secret': str(result['secret']),
                            'num_colors': result['config']['num_colors'],
                            'num_pegs': result['config']['num_pegs'],
                            'allow_duplicates': result['config']['allow_duplicates'],
                            'max_turns': result['config']['max_turns'],
                            'timestamp': result['timestamp'],
                            'input_tokens': result['total_tokens'].get('input', 0),
                            'output_tokens': result['total_tokens'].get('output', 0),
                            'total_tokens': (result['total_tokens'].get('input', 0) +
                                           result['total_tokens'].get('output', 0)),
                            'num_turns': len([t for t in result['turns'] if t.get('guess')])
                        }

                        # Apply filters
                        if filter_model and record['model'] != filter_model:
                            continue
                        if filter_outcome and record['outcome'] != filter_outcome:
                            continue

                        records.append(record)

            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}", file=sys.stderr)
                continue

    if not records:
        raise ValueError("No valid result records found")

    return pd.DataFrame(records)


def calculate_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate aggregate statistics per model.

    Returns:
        DataFrame with columns: model, total_games, wins, losses, errors, win_rate,
                                avg_turns, avg_duration, total_tokens, avg_tokens_per_game
    """
    stats = []

    for model in df['model'].unique():
        model_df = df[df['model'] == model]

        total_games = len(model_df)
        wins = len(model_df[model_df['outcome'] == 'win'])
        losses = len(model_df[model_df['outcome'] == 'loss'])
        errors = len(model_df[model_df['outcome'] == 'error'])

        win_rate = wins / total_games if total_games > 0 else 0

        # Only calculate turn stats for wins
        win_df = model_df[model_df['outcome'] == 'win']
        avg_turns = win_df['total_turns'].mean() if len(win_df) > 0 else 0
        min_turns = int(win_df['total_turns'].min()) if len(win_df) > 0 else 0
        max_turns = int(win_df['total_turns'].max()) if len(win_df) > 0 else 0
        win_turns_list = list(win_df['total_turns'].values) if len(win_df) > 0 else []

        avg_duration = model_df['duration_seconds'].mean()
        total_tokens = model_df['total_tokens'].sum()
        avg_tokens = model_df['total_tokens'].mean()

        stats.append({
            'model': model,
            'mode': model_df['mode'].iloc[0],
            'total_games': total_games,
            'wins': wins,
            'losses': losses,
            'errors': errors,
            'win_rate': win_rate,
            'avg_turns_when_won': round(avg_turns, 2),
            'min_turns': min_turns,
            'max_turns': max_turns,
            'win_turns': ', '.join(str(int(t)) for t in win_turns_list) if win_turns_list else '-',
            'avg_duration': round(avg_duration, 2),
            'total_tokens': int(total_tokens),
            'avg_tokens_per_game': round(avg_tokens, 1)
        })

    stats_df = pd.DataFrame(stats)
    stats_df = stats_df.sort_values('win_rate', ascending=False)
    return stats_df


def generate_html_report(df: pd.DataFrame, stats_df: pd.DataFrame, output_path: Path):
    """Generate HTML report with visualizations."""

    # Create figures
    fig_dir = output_path.parent / f"{output_path.stem}_files"
    fig_dir.mkdir(exist_ok=True)

    # Figure 1: Win rate comparison (bar chart)
    plt.figure(figsize=(10, 6))
    plt.bar(stats_df['model'], stats_df['win_rate'] * 100, color='steelblue')
    plt.xlabel('Model')
    plt.ylabel('Win Rate (%)')
    plt.title('Win Rate by Model')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    fig1_path = fig_dir / 'win_rate.png'
    plt.savefig(fig1_path, dpi=100)
    plt.close()

    # Figure 2: Turn distribution (box plot)
    plt.figure(figsize=(10, 6))
    win_df = df[df['outcome'] == 'win']
    if len(win_df) > 0:
        models = win_df['model'].unique()
        data_to_plot = [win_df[win_df['model'] == m]['total_turns'].values for m in models]
        plt.boxplot(data_to_plot, tick_labels=models)
        plt.xlabel('Model')
        plt.ylabel('Turns to Win')
        plt.title('Turn Distribution for Winning Games')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        fig2_path = fig_dir / 'turn_distribution.png'
        plt.savefig(fig2_path, dpi=100)
    plt.close()

    # Figure 3: Token efficiency (scatter plot)
    plt.figure(figsize=(10, 6))
    win_df = df[df['outcome'] == 'win']
    if len(win_df) > 0 and win_df['total_tokens'].sum() > 0:
        for model in win_df['model'].unique():
            model_wins = win_df[win_df['model'] == model]
            if len(model_wins) > 0:
                plt.scatter(model_wins['total_turns'], model_wins['total_tokens'],
                           label=model, alpha=0.6, s=50)
        plt.xlabel('Turns to Win')
        plt.ylabel('Total Tokens Used')
        plt.title('Token Efficiency (Winning Games)')
        plt.legend()
        plt.tight_layout()
        fig3_path = fig_dir / 'token_efficiency.png'
        plt.savefig(fig3_path, dpi=100)
    plt.close()

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mastermind LLM Benchmark Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2 {{
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .section {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .metric-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .win {{ color: #28a745; }}
        .loss {{ color: #dc3545; }}
        .error {{ color: #ffc107; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Mastermind LLM Benchmark Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p>Total Games: {len(df)} | Models Tested: {len(stats_df)}</p>
    </div>

    <div class="section">
        <h2>Summary Statistics</h2>
        <table>
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Mode</th>
                    <th>Games</th>
                    <th>Wins</th>
                    <th>Losses</th>
                    <th>Errors</th>
                    <th>Win Rate</th>
                    <th>Avg Turns (Wins)</th>
                    <th>Avg Duration (s)</th>
                    <th>Total Tokens</th>
                </tr>
            </thead>
            <tbody>
"""

    for _, row in stats_df.iterrows():
        html_content += f"""                <tr>
                    <td><strong>{row['model']}</strong></td>
                    <td>{row['mode']}</td>
                    <td>{row['total_games']}</td>
                    <td class="win">{row['wins']}</td>
                    <td class="loss">{row['losses']}</td>
                    <td class="error">{row['errors']}</td>
                    <td>{row['win_rate']*100:.1f}%</td>
                    <td>{row['avg_turns_when_won']:.1f}</td>
                    <td>{row['avg_duration']:.2f}</td>
                    <td>{row['total_tokens']:,}</td>
                </tr>
"""

    html_content += """            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Win Rate Comparison</h2>
        <img src="{stem}_files/win_rate.png" alt="Win Rate">
    </div>

    <div class="section">
        <h2>Turn Distribution (Winning Games)</h2>
        <img src="{stem}_files/turn_distribution.png" alt="Turn Distribution">
    </div>

    <div class="section">
        <h2>Token Efficiency (Winning Games)</h2>
        <img src="{stem}_files/token_efficiency.png" alt="Token Efficiency">
    </div>

    <div class="section">
        <h2>Overall Metrics</h2>
        <div class="metric">
            <div class="metric-label">Total Games</div>
            <div class="metric-value">{total_games}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Wins</div>
            <div class="metric-value">{total_wins}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Overall Win Rate</div>
            <div class="metric-value">{win_rate:.1f}%</div>
        </div>
    </div>
</body>
</html>
""".format(
    stem=output_path.stem,
    total_games=len(df),
    total_wins=stats_df['wins'].sum(),
    win_rate=stats_df['win_rate'].mean() * 100
)

    with open(output_path, 'w') as f:
        f.write(html_content)

    print(f"HTML report saved to: {output_path}")
    print(f"Supporting files in: {fig_dir}")


def generate_markdown_report(df: pd.DataFrame, stats_df: pd.DataFrame, output_path: Path):
    """Generate Markdown report."""

    md_content = f"""# Mastermind LLM Benchmark Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Games:** {len(df)}
**Models Tested:** {len(stats_df)}

## Summary Statistics

"""

    # Convert stats to markdown table
    md_content += stats_df.to_markdown(index=False)

    md_content += f"""

## Overall Metrics

- **Total Games:** {len(df)}
- **Total Wins:** {stats_df['wins'].sum()}
- **Total Losses:** {stats_df['losses'].sum()}
- **Total Errors:** {stats_df['errors'].sum()}
- **Overall Win Rate:** {stats_df['win_rate'].mean() * 100:.1f}%

## Per-Model Breakdown

"""

    for _, row in stats_df.iterrows():
        md_content += f"""### {row['model']} ({row['mode']} mode)

- **Games:** {row['total_games']}
- **Wins:** {row['wins']} ({row['win_rate']*100:.1f}%)
- **Losses:** {row['losses']}
- **Errors:** {row['errors']}
- **Average Turns (when won):** {row['avg_turns_when_won']:.1f}
- **Average Duration:** {row['avg_duration']:.2f}s
- **Total Tokens:** {row['total_tokens']:,}

"""

    with open(output_path, 'w') as f:
        f.write(md_content)

    print(f"Markdown report saved to: {output_path}")


def generate_csv_report(stats_df: pd.DataFrame, output_path: Path):
    """Generate CSV report."""
    stats_df.to_csv(output_path, index=False)
    print(f"CSV report saved to: {output_path}")


def generate_terminal_report(df: pd.DataFrame, stats_df: pd.DataFrame):
    """Print report to terminal."""

    print("\n" + "=" * 100)
    print("MASTERMIND LLM BENCHMARK REPORT")
    print("=" * 100)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Games: {len(df)} | Models Tested: {len(stats_df)}")
    print("=" * 100)

    print("\nSUMMARY STATISTICS")
    print("-" * 100)

    # Format table for terminal
    table_data = []
    for _, row in stats_df.iterrows():
        table_data.append([
            row['model'],
            row['total_games'],
            row['wins'],
            row['losses'],
            f"{row['win_rate']*100:.1f}%",
            f"{row['avg_turns_when_won']:.1f}" if row['wins'] > 0 else '-',
            f"{row['min_turns']}-{row['max_turns']}" if row['wins'] > 0 else '-',
            row['win_turns'] if row['wins'] > 0 else '-',
        ])

    headers = ['Model', 'Games', 'Wins', 'Losses', 'Win Rate', 'Avg Turns', 'Min-Max', 'Win Turns']

    print(tabulate(table_data, headers=headers, tablefmt='grid'))

    print("\n" + "=" * 100)
    print(f"Overall Win Rate: {stats_df['win_rate'].mean() * 100:.1f}%")
    print("=" * 100 + "\n")


def main():
    """Main reporter entry point."""
    parser = argparse.ArgumentParser(
        description="Generate reports from Mastermind LLM benchmark results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all report formats
  python -m src.reporter --input "outputs/orchestrator_*.jsonl" \\
    --format html,markdown,csv,terminal

  # Generate HTML report only
  python -m src.reporter --input "outputs/*.jsonl" --format html

  # Filter by model
  python -m src.reporter --input "outputs/*.jsonl" \\
    --filter-model claude --format terminal

  # Custom output location
  python -m src.reporter --input "outputs/*.jsonl" \\
    --format html --output reports/my_report
        """
    )

    parser.add_argument('--input', type=str, action='append',
                        default=None,
                        help='Input glob pattern(s) for JSONL files (default: outputs/*.jsonl)')
    parser.add_argument('--format', type=str, default='terminal',
                        help='Output format(s): html,markdown,csv,terminal (comma-separated, default: terminal)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output basename (default: reports/report_TIMESTAMP)')
    parser.add_argument('--filter-model', type=str, default=None,
                        help='Filter by model name')
    parser.add_argument('--filter-outcome', type=str, choices=['win', 'loss', 'error'],
                        help='Filter by outcome')

    args = parser.parse_args()

    # Default input pattern
    if args.input is None:
        args.input = ['outputs/*.jsonl']

    # Parse formats
    formats = [f.strip().lower() for f in args.format.split(',')]
    valid_formats = {'html', 'markdown', 'csv', 'terminal'}
    invalid = set(formats) - valid_formats
    if invalid:
        parser.error(f"Invalid format(s): {', '.join(invalid)}")

    # Default output basename
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_basename = f"reports/report_{timestamp}"
    else:
        output_basename = args.output

    # Ensure reports directory exists
    output_path = Path(output_basename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load results
    try:
        df = load_results(args.input, args.filter_model, args.filter_outcome)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df)} result(s) from {len(df['file'].unique())} file(s)")

    # Calculate statistics
    stats_df = calculate_statistics(df)

    # Generate reports
    for fmt in formats:
        if fmt == 'html':
            generate_html_report(df, stats_df, output_path.with_suffix('.html'))
        elif fmt == 'markdown':
            generate_markdown_report(df, stats_df, output_path.with_suffix('.md'))
        elif fmt == 'csv':
            generate_csv_report(stats_df, output_path.with_suffix('.csv'))
        elif fmt == 'terminal':
            generate_terminal_report(df, stats_df)

    print("\nReport generation complete!")


if __name__ == '__main__':
    main()
