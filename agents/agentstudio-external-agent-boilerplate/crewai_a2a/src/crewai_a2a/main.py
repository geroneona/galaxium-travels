#!/usr/bin/env python
import sys
import warnings
import json

from crewai_a2a.flow import BoilerplateFlow


warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def run():
    """
    Run the crew with optional CLI arguments as user input.
    Usage: crewai "your input text here"
    """
    # Get user input from CLI arguments, or use empty string if none provided
    user_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    try:
        flow = BoilerplateFlow()
        flow.kickoff(inputs={"user_input": user_text})  # inputs={"user_text": user_text})
        print(f"Answer: {flow.state.answer}")
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    """

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {"crewai_trigger_payload": trigger_payload, "topic": "", "current_year": ""}

    try:
        result = BoilerplateFlow().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
