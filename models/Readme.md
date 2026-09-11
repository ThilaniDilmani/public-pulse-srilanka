# Public Pulse — Fine-Tuned Models

> **Model artifacts for the Public Pulse multilingual NLP inference pipeline**

This directory contains the model metadata, configuration, label mappings, and documentation for the fine-tuned NLP models used by **Public Pulse — Civic Intelligence for Sri Lankan Public Discourse**.

The fine-tuned model weights are intentionally **not stored in this GitHub repository** because the checkpoint files are large. The trained model artifacts are distributed separately through the project's Google Drive repository.

---

## Table of Contents

- [Overview](#overview)
- [Model Architecture](#model-architecture)
- [Model Inventory](#model-inventory)
- [Layer 1 — Utility Classification](#layer-1--utility-classification)
- [Layer 2 — Topic Classification](#layer-2--topic-classification)
- [Layer 4 — Stance Classification](#layer-4--stance-classification)
- [Model Storage](#model-storage)
- [Downloading the Fine-Tuned Models](#downloading-the-fine-tuned-models)
- [Installing the Models](#installing-the-models)
- [Expected Directory Structure](#expected-directory-structure)
- [Verifying the Installation](#verifying-the-installation)
- [Inference Pipeline](#inference-pipeline)
- [Layer 3 — Important Note](#layer-3--important-note)
- [Reproducibility](#reproducibility)
- [Model Versioning](#model-versioning)
- [Security and Privacy](#security-and-privacy)
- [Troubleshooting](#troubleshooting)
- [For New Team Members](#for-new-team-members)
- [Model Management Policy](#model-management-policy)
- [Checklist](#checklist)

---

# Overview

Public Pulse analyzes public discourse from Sri Lankan TV news YouTube
comments using a multilingual NLP pipeline.

The project works with real-world user-generated text that can contain:

- Sinhala
- Singlish
- English
- Tamil
- Code-switched text
- Informal language
- Spelling variations
- Noisy or irrelevant comments

The classification pipeline uses fine-tuned **XLM-RoBERTa** models to
progressively process the collected comments.

The current model pipeline consists of:

```text
Layer 1 → Utility Classification
Layer 2 → Topic Classification
Layer 4 → Stance Classification
