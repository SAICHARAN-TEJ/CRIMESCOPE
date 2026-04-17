"""
Eight specialised agent archetypes distributed across 1,000 agents.

Each archetype inherits from BaseAgent and overrides
ARCHETYPE, COUNT, MODEL, and BIAS.
"""

from backend.agents.base_agent import BaseAgent
from backend.config import settings


class ForensicAnalyst(BaseAgent):
    ARCHETYPE = "forensic_analyst"
    COUNT = 120
    MODEL = settings.llm_model_name
    BIAS = (
        "Focus exclusively on physical evidence, trace analysis, and technical data. "
        "Skeptical of human testimony."
    )


class BehavioralProfiler(BaseAgent):
    ARCHETYPE = "behavioral_profiler"
    COUNT = 100
    MODEL = settings.reasoning_model_name
    BIAS = (
        "Prioritise psychological markers, victimology, and offender motivation. "
        "Look for deviations from normal behavioural patterns."
    )


class EyewitnessSimulator(BaseAgent):
    ARCHETYPE = "eyewitness_simulator"
    COUNT = 150
    MODEL = settings.llm_model_name
    BIAS = (
        "Simulate observation errors, lighting conditions, and cognitive bias "
        "in human recall. Question every statement."
    )


class SuspectPersona(BaseAgent):
    ARCHETYPE = "suspect_persona"
    COUNT = 200
    MODEL = settings.llm_model_name
    BIAS = (
        "Defensive, deceptive, and self-preserving. Exploit gaps in physical "
        "evidence. Assume innocence and challenge the prosecution."
    )


class AlibiVerifier(BaseAgent):
    ARCHETYPE = "alibi_verifier"
    COUNT = 80
    MODEL = settings.llm_model_name
    BIAS = (
        "Focus on timeline gaps and digital footprint verification. "
        "Cross-reference disparate data points for inconsistencies."
    )


class SceneReconstructor(BaseAgent):
    ARCHETYPE = "scene_reconstructor"
    COUNT = 120
    MODEL = settings.llm_model_name
    BIAS = (
        "Prioritise spatial relationships and physical logistics. "
        "Can X have happened at Y in Z time?"
    )


class StatisticalBaseline(BaseAgent):
    ARCHETYPE = "statistical_baseline"
    COUNT = 130
    MODEL = settings.fast_model_name
    BIAS = (
        "Base judgements on historical probability and base rates "
        "for similar crimes, locations, and demographics."
    )


class ContradictionDetector(BaseAgent):
    ARCHETYPE = "contradiction_detector"
    COUNT = 100
    MODEL = settings.reasoning_model_name
    BIAS = (
        "Pure logic gate. Find inconsistencies between agents, evidence "
        "clusters, and timeline reports."
    )


# Ordered list for the SwarmManager to iterate
ALL_ARCHETYPES = [
    ForensicAnalyst,
    BehavioralProfiler,
    EyewitnessSimulator,
    SuspectPersona,
    AlibiVerifier,
    SceneReconstructor,
    StatisticalBaseline,
    ContradictionDetector,
]
