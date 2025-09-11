#!/usr/bin/env python3
"""
AI Context Maintenance Script

This script helps maintain and update the AI context files.
"""

import json
from pathlib import Path


def validate_json_files():
    """Validate all JSON files in the AI_CONTEXT directory"""
    context_dir = Path(__file__).parent
    json_files = list(context_dir.glob("*.json"))

    print("Validating JSON files...")
    for json_file in json_files:
        try:
            with open(json_file) as f:
                json.load(f)
            print(f"OK {json_file.name} - Valid JSON")
        except json.JSONDecodeError as e:
            print(f"ERROR {json_file.name} - Invalid JSON: {e}")
            return False
        except Exception as e:
            print(f"ERROR {json_file.name} - Error: {e}")
            return False

    print("All JSON files are valid!")
    return True


def get_file_sizes():
    """Get file sizes for all AI context files"""
    context_dir = Path(__file__).parent
    files = list(context_dir.glob("*"))

    print("\nFile sizes:")
    total_size = 0
    for file in sorted(files):
        if file.is_file():
            size = file.stat().st_size
            total_size += size
            print(f"  {file.name}: {size:,} bytes")

    print(f"\nTotal size: {total_size:,} bytes ({total_size/1024:.1f} KB)")


def merge_to_single_file():
    """Merge all JSON files into a single AI_CONTEXT.json file"""
    context_dir = Path(__file__).parent
    json_files = list(context_dir.glob("*.json"))

    merged_data = {}

    for json_file in json_files:
        if json_file.name == "AI_CONTEXT.json":
            continue  # Skip the original file if it exists

        with open(json_file) as f:
            data = json.load(f)
            merged_data.update(data)

    # Write merged file
    output_file = context_dir / "AI_CONTEXT.json"
    with open(output_file, "w") as f:
        json.dump(merged_data, f, indent=2)

    print(f"Merged {len(json_files)} files into {output_file.name}")
    print(f"Size: {output_file.stat().st_size:,} bytes")


def split_from_single_file():
    """Split a single AI_CONTEXT.json file into multiple files"""
    context_dir = Path(__file__).parent
    input_file = context_dir / "AI_CONTEXT.json"

    if not input_file.exists():
        print("AI_CONTEXT.json not found!")
        return

    with open(input_file) as f:
        data = json.load(f)

    # Define file mappings
    file_mappings = {
        "core.json": [
            "ai_context",
            "project",
            "ai_assistant_rules",
            "never_delete_critical_files",
        ],
        "architecture.json": [
            "project_architecture",
            "development_workflow",
            "decision_history",
        ],
        "user_experience.json": [
            "user_experience",
            "technical_debt",
            "development_insights",
        ],
        "troubleshooting.json": ["troubleshooting_guide", "common_issues_solutions"],
        "learning_history.json": [
            "conversation_learnings",
            "current_session_context",
            "ai_effectiveness_optimization",
        ],
    }

    for filename, keys in file_mappings.items():
        file_data = {}
        for key in keys:
            if key in data:
                file_data[key] = data[key]

        output_file = context_dir / filename
        with open(output_file, "w") as f:
            json.dump(file_data, f, indent=2)

        print(f"Created {filename} with {len(file_data)} sections")


def main():
    """Main function"""
    print("AI Context Maintenance Script")
    print("=" * 40)

    while True:
        print("\nOptions:")
        print("1. Validate JSON files")
        print("2. Show file sizes")
        print("3. Merge to single file")
        print("4. Split from single file")
        print("5. Exit")

        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == "1":
            validate_json_files()
        elif choice == "2":
            get_file_sizes()
        elif choice == "3":
            merge_to_single_file()
        elif choice == "4":
            split_from_single_file()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
