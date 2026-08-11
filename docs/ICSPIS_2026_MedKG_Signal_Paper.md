# ICSPIS 2026 Paper Submission Pack

## EDAS Form Fill (ICSPIS 2026)

1. Conference Track  
Track 4: Signal Processing for Medical Applications

2. Paper Title  
MedKG-Signal: Knowledge Graph-Augmented Multimodal Medical AI for Interpretable Clinical Risk Prediction

3. Abstract  
Clinical decision support systems frequently underperform in real hospital workflows because they process fragmented modalities and provide limited evidence traceability. This paper presents MedKG-Signal, a medical AI framework that integrates physiological signal features, clinical text embeddings, and a heterogeneous medical knowledge graph for interpretable risk prediction. The proposed graph links patient encounters, diagnoses, symptoms, medications, laboratory findings, and signal-derived phenotypes using ontology-aligned relations and temporal co-occurrence constraints. A relation-aware graph encoder is jointly trained with signal and text encoders to learn robust patient representations for downstream prediction tasks. To improve trustworthiness, we introduce a graph-grounded explanation module that generates evidence-backed rationales constrained by valid clinical paths, reducing unsupported claims in generated outputs. The framework is designed for intensive-care and longitudinal hospital data settings where multimodal context is essential. Experimental protocol and ablation design are provided for mortality and diagnosis prediction tasks, with evaluation metrics covering predictive performance, calibration, and explanation quality. MedKG-Signal offers a practical pathway toward safer, more transparent medical AI by combining signal processing and knowledge-centric reasoning in a unified architecture.

4. Keywords  
Medical AI; Knowledge Graph; Clinical Decision Support; Multimodal Learning; Explainable AI; Physiological Signal Processing

5. Primary Topic Area  
AI for medical signal processing and interpretable clinical intelligence

6. Paper Type  
Full Paper (4-6 pages, IEEE two-column format)

---

## Manuscript Draft (Ready to paste into IEEE template)

### Title
MedKG-Signal: Knowledge Graph-Augmented Multimodal Medical AI for Interpretable Clinical Risk Prediction

### Authors
First Author, Second Author, Third Author  
Department/Institute, University/Organization, Country  
Email: first.author@domain.com

### Abstract
Clinical decision support systems frequently underperform in real hospital workflows because they process fragmented modalities and provide limited evidence traceability. This paper presents MedKG-Signal, a medical AI framework that integrates physiological signal features, clinical text embeddings, and a heterogeneous medical knowledge graph for interpretable risk prediction. The proposed graph links patient encounters, diagnoses, symptoms, medications, laboratory findings, and signal-derived phenotypes using ontology-aligned relations and temporal co-occurrence constraints. A relation-aware graph encoder is jointly trained with signal and text encoders to learn robust patient representations for downstream prediction tasks. To improve trustworthiness, we introduce a graph-grounded explanation module that generates evidence-backed rationales constrained by valid clinical paths, reducing unsupported claims in generated outputs. The framework is designed for intensive-care and longitudinal hospital data settings where multimodal context is essential. Experimental protocol and ablation design are provided for mortality and diagnosis prediction tasks, with evaluation metrics covering predictive performance, calibration, and explanation quality. MedKG-Signal offers a practical pathway toward safer, more transparent medical AI by combining signal processing and knowledge-centric reasoning in a unified architecture.

### Index Terms
Medical AI, knowledge graph, multimodal learning, explainable AI, clinical decision support, physiological signal processing.

---

### I. Introduction
Recent advances in deep learning have improved performance in many medical prediction tasks, including mortality estimation, diagnosis coding, and adverse-event warning. However, real-world adoption remains limited because most systems fail to provide reliable reasoning paths that clinicians can inspect and trust. Hospital data is inherently multimodal: electrocardiography and bedside waveforms encode temporal physiological dynamics, while clinical notes and laboratory data provide semantic and contextual meaning. Learning from these modalities independently often leads to inconsistent predictions and weak generalization.

Knowledge graphs offer a structured mechanism to integrate heterogeneous medical information. By representing entities (diseases, symptoms, medications, biomarkers, waveform phenotypes) and typed relations, a knowledge graph can support explicit reasoning, provenance tracking, and explainability. Yet many existing medical KG systems either ignore signal-level features or treat graph construction as a static preprocessing step disconnected from predictive learning.

This work proposes MedKG-Signal, a unified framework that fuses physiological signal processing, clinical text representation, and graph neural reasoning. Our goal is to improve both predictive quality and interpretability by forcing model outputs to align with clinically valid graph paths. The main contributions are:

1. A heterogeneous medical KG construction workflow combining EHR entities, signal-derived phenotypes, and ontology-mapped relations.
2. A multimodal relational encoder for patient-level prediction.
3. A graph-grounded explanation mechanism with path validation and uncertainty-aware output filtering.
4. A reproducible evaluation protocol for predictive and explanation-centric metrics.

---

### II. Related Work
Medical AI literature includes three relevant strands.

1. Clinical multimodal learning: Models combining structured variables and text have shown gains over unimodal approaches, especially in intensive-care settings. However, explicit symbolic knowledge is usually absent.

2. Graph neural networks in healthcare: Prior work uses graph convolution and relational graph models for diagnosis prediction and medication recommendation. These methods often rely on code-level co-occurrence graphs and rarely incorporate physiological signal abstractions.

3. Grounded explanation and RAG in medicine: Retrieval-augmented methods improve factuality but can still produce unsupported statements if retrieval lacks ontology-level constraints.

MedKG-Signal addresses this gap by integrating signal features into KG nodes and constraining explanation generation using validated graph paths.

---

### III. Methodology

#### A. Heterogeneous Medical Knowledge Graph
We define a graph G=(V,E,R) with node types:
- Patient encounter
- Diagnosis concept
- Symptom concept
- Medication
- Laboratory marker
- Signal phenotype
- Clinical evidence snippet

Edges include:
- Encounter-has-diagnosis
- Encounter-has-symptom
- Medication-treats-diagnosis
- Lab-supports-diagnosis
- Signal-phenotype-indicates-condition
- Evidence-supports-relation

Each edge stores confidence, timestamp window, and provenance metadata. Standard clinical vocabularies (for example diagnosis, medication, and lab ontologies) are used for normalization.

#### B. Signal and Text Encoders
Given encounter p, let x_sig be waveform segments and x_txt be note tokens.

Signal encoder:

s_p = f_s(x_sig)

Text encoder:

t_p = f_t(x_txt)

Initial fusion:

z_p = W_s s_p + W_t t_p

#### C. Relation-Aware Graph Encoding
For node i at layer l:

h_i^(l+1) = sigma( W_0^(l) h_i^(l) + sum over r in R [ 1/|N_r(i)| * sum over j in N_r(i) [ W_r^(l) h_j^(l) ] ] )

Final encounter representation:

h_hat_p = lambda z_p + (1-lambda) h_p^(L)

#### D. Training Objective
The joint loss is:

L = L_pred + alpha L_link + beta L_contrast

where:
- L_pred is prediction loss (classification),
- L_link enforces KG relation consistency,
- L_contrast aligns multimodal and graph-neighborhood representations.

#### E. Graph-Grounded Explanation
For each predicted output, top-k supporting graph neighborhoods are retrieved. Explanation text is generated only from retrieved evidence, then validated against allowed relation chains. Claims not mapped to valid paths are suppressed or flagged as uncertain.

---

### IV. Experimental Design

#### A. Tasks
1. In-hospital mortality risk prediction  
2. Primary diagnosis group prediction

#### B. Baselines
- Signal-only model
- Text-only model
- Early fusion (signal + text, no KG)
- KG without signal phenotype nodes
- Unconstrained retrieval-based explainer

#### C. Metrics
- Predictive: AUROC, Macro-F1, AUPRC
- Calibration: ECE
- Explanation quality: evidence precision, unsupported claim rate, clinician usefulness score

#### D. Ablation Plan
We test the contribution of:
- Signal phenotype nodes
- Ontology constraints
- Evidence edges
- Contrastive alignment term

---

### V. Results and Discussion
MedKG-Signal is expected to provide the largest gains in clinically ambiguous and multi-morbidity cases where single-modality models are weak. The graph layer improves semantic coherence between symptoms, diagnoses, and interventions, while signal phenotypes contribute temporal acuity. The explanation module enhances clinician trust by exposing path-based reasoning rather than opaque logits.

Use the following table in your final paper with measured values from your runs:

| Model | AUROC | Macro-F1 | AUPRC | ECE | Unsupported Claim Rate |
|---|---:|---:|---:|---:|---:|
| Signal-only | [ ] | [ ] | [ ] | [ ] | [ ] |
| Text-only | [ ] | [ ] | [ ] | [ ] | [ ] |
| Fusion (no KG) | [ ] | [ ] | [ ] | [ ] | [ ] |
| KG (no signal phenotypes) | [ ] | [ ] | [ ] | [ ] | [ ] |
| MedKG-Signal (proposed) | [ ] | [ ] | [ ] | [ ] | [ ] |

---

### VI. Limitations
The framework depends on high-quality ontology mapping and may require institution-specific tuning. Real-time deployment constraints (latency and graph refresh cost) should be addressed before bedside integration.

---

### VII. Conclusion
This paper presents MedKG-Signal, a knowledge graph-augmented multimodal medical AI framework that combines physiological signal processing, clinical text understanding, and relation-aware reasoning. The system is designed to improve both predictive performance and interpretability through graph-grounded evidence paths and uncertainty-aware explanations. The approach is aligned with safety-critical clinical workflows and offers a practical blueprint for deployable, transparent medical AI.

---

### References (IEEE style starter list)
[1] A. E. W. Johnson et al., "MIMIC-IV, a freely accessible electronic health record dataset," Scientific Data.  
[2] O. Bodenreider, "The Unified Medical Language System (UMLS)," Nucleic Acids Research.  
[3] T. N. Kipf and M. Welling, "Semi-Supervised Classification with Graph Convolutional Networks," ICLR.  
[4] M. Schlichtkrull et al., "Modeling Relational Data with Graph Convolutional Networks," ESWC.  
[5] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," NeurIPS.  
[6] Recent medical KG and multimodal clinical prediction papers relevant to your exact dataset and task.
