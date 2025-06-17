# evalllm2025
Code source des scripts utilisés par Kairntech lors de la campagne EvalLLM 2025
Environnement python 3.8

## Script de conversion du format json Kairntech au format json EvalLLM
evalllm_vote.py
```
python evalllm_vote.py data/run1.json data/run2.json output
```

## Script de génération d'un run de "vote" entre 2 runs existants
json2evalllm.py
```
python json2evalllm.py data/src_events.json output
```

