# PulseAI Research Intelligence Report

Generated at: 2026-03-28T13:02:49.170515+00:00

## Summary

- Total sources scanned: 10
- Reachable sources: 10
- Datasets: 4
- Papers: 2
- Repositories: 3
- Pretrained candidates: 1

## Source Details

### MIT-BIH Arrhythmia Database (dataset)

- URL: https://physionet.org/content/mitdb/1.0.0/
- Status: OK (200)
- Title: MIT-BIH Arrhythmia Database v1.0.0
- Why it matters: Gold-standard beat annotations for binary arrhythmia detection benchmarking.

### MIT-BIH Noise Stress Test Database (dataset)

- URL: https://physionet.org/content/nstdb/1.0.0/
- Status: OK (200)
- Title: MIT-BIH Noise Stress Test Database v1.0.0
- Why it matters: Directly supports robustness testing under ambulatory noise.

### PTB-XL (dataset)

- URL: https://physionet.org/content/ptb-xl/1.0.3/
- Status: OK (200)
- Title: PTB-XL, a large publicly available electrocardiography dataset v1.0.3
- Why it matters: Large-scale ECG dataset with recommended train/val/test folds and rich metadata.

### INCART 12-lead Arrhythmia Database (dataset)

- URL: https://physionet.org/content/incartdb/1.0.0/
- Status: OK (200)
- Title: St Petersburg INCART 12-lead Arrhythmia Database v1.0.0
- Why it matters: External-domain arrhythmia data for generalization checks.

### Deep Learning for ECG Analysis: Benchmarks and Insights from PTB-XL (paper)

- URL: https://arxiv.org/abs/2004.13701
- Status: OK (200)
- Title: [2004.13701] Deep Learning for ECG Analysis: Benchmarks and Insights from PTB-XL
- Why it matters: Benchmarking blueprint and transfer-learning guidance for ECG models.

### ECG Heartbeat Classification: A Deep Transferable Representation (paper)

- URL: https://arxiv.org/abs/1805.00794
- Status: OK (200)
- Title: [1805.00794] ECG Heartbeat Classification: A Deep Transferable Representation
- Why it matters: Transfer-learning strategy across arrhythmia and related ECG tasks.

### resnet1d (repo)

- URL: https://github.com/hsd1503/resnet1d
- Status: OK (200)
- Title: GitHub - hsd1503/resnet1d: PyTorch implementations of several SOTA backbone deep neural networks (such as ResNet, ResNeXt, RegNet) on one-dimensional (1D) signa
- Why it matters: Strong 1D backbone family for signal tasks; useful for model refresh experiments.

### automatic-ecg-diagnosis (repo)

- URL: https://github.com/antonior92/automatic-ecg-diagnosis
- Status: OK (200)
- Title: GitHub - antonior92/automatic-ecg-diagnosis: Scripts and modules for training and testing neural network for ECG automatic classification. Companion code to the
- Why it matters: Well-known ECG classification training pipeline with publication lineage.

### py-ecg-detectors (repo)

- URL: https://github.com/berndporr/py-ecg-detectors
- Status: OK (200)
- Title: GitHub - berndporr/py-ecg-detectors: Popular ECG QRS detectors written in python · GitHub
- Why it matters: Reference QRS detector implementations to harden preprocessing and HR estimates.

### PTB-XL benchmark checkpoints ecosystem (pretrained_candidate)

- URL: https://arxiv.org/abs/2004.13701
- Status: OK (200)
- Title: [2004.13701] Deep Learning for ECG Analysis: Benchmarks and Insights from PTB-XL
- Why it matters: Candidate source for initialization and transfer to single-lead edge model.

## Execution Recommendations

- Prioritize PTB-XL transfer pretraining, then fine-tune on MIT-BIH rhythm targets.
- Add noise-stress evaluation (NSTDB) to quantify robustness before deployment.
- Benchmark at least one ResNet1D baseline against the current HCTG-Net model.
- Gate deployment by constrained metrics (specificity floor + recall floor), not accuracy alone.
