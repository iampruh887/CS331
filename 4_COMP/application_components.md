# II. Application Components

Based on the SRS and Class Specifications, the key application components in the Nexus project are:

* **Authentication Service:**
    * **Role:** Security Gatekeeper.
    * **Function:** Validates user identity via an external Identity Provider and manages sessions to ensure only authorized users access task execution features.
* **NLP Engine:**
    * **Role:** Input Processor.
    * **Function:** Parses natural language commands to identify the **Intent** (Action) and **Entities** (Parameters) with a target accuracy of 85%.
* **Context Manager:**
    * **Role:** Short-term Memory.
    * **Function:** Stores the context of the last 3 messages to resolve references (e.g., understanding "restart **it**" refers to the previously mentioned server).
* **Task Executor:**
    * **Role:** Central Orchestrator.
    * **Function:** Coordinates the execution. It checks if confirmation is needed for write actions, masks sensitive outputs, and triggers the appropriate script.
* **Script Registry:**
    * **Role:** Plugin Manager.
    * **Function:** Manages the registration and metadata of external scripts (Python/Bash) that the system can execute.
* **Audit Logger:**
    * **Role:** Compliance Recorder.
    * **Function:** Maintains an immutable record of every action, including User ID, Command, Timestamp, and Result.
* **Self-Correction Engine:**
    * **Role:** Automated Troubleshooter (Novelty Feature).
    * **Function:** Analyzes error logs when a task fails and automatically suggests potential fixes to the user.
* **Calendar Integration:**
    * **Role:** External API Handler.
    * **Function:** Interfaces with external Calendar APIs to check availability and schedule meetings based on natural language requests.