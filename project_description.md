# Project Description: Intelligent Self-Healing Distributed Storage Platform

## Overview
The Intelligent Self-Healing Distributed Storage Platform is an advanced distributed systems sandbox structured to emulate enterprise-grade storage architectures (such as SAN/NAS systems). Moving beyond rudimentary file sharing, the platform is designed to provide resilient, scalable, and intelligent storage operations by distributing files across independent node containers while centrally orchestrating metadata and fault-tolerance via a backend master server.

## Core Architectural Components

### 1. Master Server (FastAPI + General Purpose Orchestration)
The brain of the system. Responsibilities include:
- Processing HTTP requests from the client.
- Orchestrating Authentication (JWT-based).
- Executing a **Weighted Storage Placement Engine** to resolve the cheapest, most efficient node to park user files.
- Communicating asynchronously with backend cluster nodes to trigger data workflows.

### 2. Distributed Storage Nodes (Independent FastAPI Daemons)
A fleet of independently operating data siloes (Node 1, Node 2, and Node 3) acting as chunk-storage endpoints. 
- They store actual blob data on their distinct mounted volumes.
- They emit constant heartbeat metrics back to the Master API indicating their health, storage limits, and artificial network latency.

### 3. State Management (PostgreSQL Database)
The relational metadata catalog that supports the file index. Tracks granular data:
- File metadata, permissions, and multi-node location catalogs.
- Real-time audit logs of chunk migrations and replication workflows.
- Central system topology reporting (capturing historical metrics for node performance).

### 4. Admin Telemetry & Client (React + Vite)
A dynamic, micro-transition equipped UI presenting detailed analytics:
- **Topology Map**: Visualizes the layout of the cluster and identifies failing nodes.
- **Chaos Engine Control Panel**: A testing playground for administrators to manually fail nodes, bump latency, or limit storage directly in runtime.
- **My Files / Drive View**: Traditional file interaction views (upload, share permissions, download).

## Technical Achievements & Advanced Functionality

* **Self-Healing Automation**:
  Through persistent health monitoring, the Master server detects unreachable nodes. When a primary data node degrades or faults entirely, the Replication Engine isolates the failure and issues background tasks to clone available file replicas into surviving active nodes, maintaining the globally defined Replication Factor dynamically.
  
* **Chaos Engineering Lifecycle**:
  Emulating "Monkey Testing", administrators are equipped with the UI toggles to artificially alter node performance parameters (simulating 500ms latency or CPU overload thresholds). This forces the Master API to re-calculate its Weighted Placement strategy in real-time, effectively steering new uploads away from degraded network paths instantly.

* **Versioning & Global Deduplication**:
  Multiple uploads of identical documents are checked against global hash ledgers (SHA-256). Identical objects yield symbolic link relations inside the database rather than physical blob cloning. Modifying deduplicated documents provisions copy-on-write version tracking for seamless linear rollback.
