import json
from crewai import Crew, Task, Process
from backend.agents.finance_agents import FinanceProcessingAgents

def run_agent(name: str, agent, input_key: str, input_value):
    """
    Wrap a single Agent in a one-task Crew, kickoff, and return the raw output.
    """
    task = Task(
        description=f"Testing {name} with {{{input_key}}}",
        expected_output="(any)",
        agent=agent,
        context=[]
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,            # turn on prompt/tool call logging
        max_execution_time=60,
        max_iter=1
    )
    result = crew.kickoff(inputs={input_key: input_value})
    # Extract the raw result string from CrewOutput
    return result.raw_output if hasattr(result, 'raw_output') else str(result)

if __name__ == "__main__":
    factory = FinanceProcessingAgents()

    # 1. Preprocessor Agent
    test_email = {
        "subject": "Netflix Subscription Renewal",
        "body": "<div>Your Netflix subscription of ₹649 will be charged on 15 Feb 2024</div>",
        "from": "netflix@example.com",
        "message_id": "test123",
        "date": "2024-01-15T10:00:00Z"
    }
    pre = factory.create_preprocessor_agent()
    pre_out = run_agent("Preprocessor", pre, "email", test_email)
    print("\n--- Preprocessor Output ---")
    print(pre_out)  # Print raw string output

    # 2. Entity Extraction Agent
    cleaned = pre_out  # The preprocessor output is already cleaned text
    ext = factory.create_entity_extractor_agent()
    ext_out = run_agent("EntityExtractor", ext, "text", cleaned)
    print("\n--- Entity Extraction Output ---")
    print(ext_out)  # Print raw string output

    # 3. Schema Validation Agent
    validator = factory.create_schema_validator_agent()
    try:
        # Try to parse if it's JSON
        parsed = json.loads(ext_out) if isinstance(ext_out, str) else ext_out
    except json.JSONDecodeError:
        parsed = ext_out  # Use as is if not JSON
    val_out = run_agent("SchemaValidator", validator, "data", parsed)
    print("\n--- Schema Validation Output ---")
    print(val_out)  # Print raw string output

    # 4. Classification Agent
    classifier = factory.create_classifier_agent()
    try:
        # Try to extract validated data if available
        if isinstance(val_out, str):
            val_data = json.loads(val_out)
        else:
            val_data = val_out
        class_in = val_data.get('validated_data') if isinstance(val_data, dict) and 'validated_data' in val_data else val_data
    except (json.JSONDecodeError, AttributeError):
        class_in = val_out  # Use as is if parsing fails
    class_out = run_agent("Classifier", classifier, "data", class_in)
    print("\n--- Classification Output ---")
    print(class_out)  # Print raw string output

    # 5. Deduplication Agent
    deduper = factory.create_validator_deduplicator_agent()
    try:
        # Try to parse if JSON string
        if isinstance(class_out, str):
            class_data = json.loads(class_out)
        else:
            class_data = class_out
    except json.JSONDecodeError:
        class_data = class_out  # Use as is if parsing fails
    dup_out = run_agent("Deduplicator", deduper, "input", [class_data, []])
    print("\n--- Deduplication Output ---")
    print(dup_out)  # Print raw string output

    # 6. State Updater Agent (Database Operations)
    updater = factory.create_state_updater_agent()
    try:
        # Try to get unique entities from deduplication output
        if isinstance(dup_out, str):
            dup_data = json.loads(dup_out)
        else:
            dup_data = dup_out
        unique_entities = dup_data.get('unique_entities') if isinstance(dup_data, dict) else dup_data
    except (json.JSONDecodeError, AttributeError):
        unique_entities = dup_out  # Use as is if parsing fails
    update_out = run_agent("StateUpdater", updater, "data", unique_entities)
    print("\n--- State Updater Output ---")
    print(update_out)  # Print raw string output

    # 7. Notifier Agent
    notifier = factory.create_notifier_agent()
    notify_out = run_agent("Notifier", notifier, "data", update_out)
    print("\n--- Notifier Output ---")
    print(notify_out)  # Print raw string output 