"""
Simulation configuration smart generator
useLLM 、Document content、 
 ， 

Adopt a step-by-step generation strategy， ：
1. Build time configuration
2. Generate event configuration
3. Batch generationAgentConfiguration
4. Generate platform configuration
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, t
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('crimescope.simulation_config')

#  （ ）
CHINA_TIMEZONE_CONFIG = {
    #  （Almost no activity）
    "dead_hours": [0, 1, 2, 3, 4, 5],
    # morning session（ ）
    "morning_hours": [6, 7, 8],
    # working hours
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    # evening peak（ ）
    "peak_hours": [19, 20, 21, 22],
    #  （ ）
    "night_hours": [23],
    # activity coefficient
    "activity_multipliers": {
        "dead": 0.05,      # Almost no one in the early morning
        "morning": 0.4,    #  
        "work": 0.7,       # Moderate working hours
        "peak": 1.5,       # evening peak
        "night": 0.5       #  
    }
}


@dataclass
class AgentActivityConfig:
    """singleAgentactivity configuration"""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    
    #   (0.0-1.0)
    activity_level: float = 0.5  #  
    
    # speaking frequency（ ）
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    
    # Active time period（24 ，0-23）
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    
    #  （ ， ：Simulation minutes）
    response_delay_min: int = 5
    response_delay_max: int = 60
    
    #   (-1.0arrive1.0， )
    sentiment_bias: float = 0.0
    
    #  （ ）
    stance: str = "neutral"  # supportive, opposing, neutral, observer
    
    # influence weight（ Agent ）
    influence_weight: float = 1.0


@dataclass  
class TimeSimulationConfig:
    """ （ ）"""
    # Total simulation time（ ）
    total_simulation_hours: int = 72  #  72Hour（3 ）
    
    #  （Simulation minutes）- default60minute（1Hour），Speed ​​up the flow of time
    minutes_per_round: int = 60
    
    #  Agent 
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20
    
    # peak hours（evening19-22point， ）
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5
    
    # Trough period（ 0-5point，Almost no activity）
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05  #  
    
    # morning session
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4
    
    # working hours
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """event configuration"""
    #  （ ）
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    
    #  （ ）
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    
    #  
    hot_topics: List[str] = field(default_factory=list)
    
    #  
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """ """
    platform: str  # twitter or reddit
    
    #  
    recency_weight: float = 0.4  #  
    popularity_weight: float = 0.3  #  
    relevance_weight: float = 0.3  #  
    
    #  （ ）
    viral_threshold: int = 10
    
    #  （ ）
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """ """
    # Basic information
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    
    # Time configuration
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    
    # Agent 
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    
    # event configuration
    event_config: EventConfig = field(default_factory=EventConfig)
    
    # Platform configuration
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None
    
    # LLMConfiguration
    llm_model: str = ""
    llm_base_url: str = ""
    
    #  
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # LLM 
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert toJSON """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    Simulation configuration smart generator
    
    useLLMAnalyze simulation requirements、Document content、 ，
     
    
    Adopt a step-by-step generation strategy：
    1.  （ ）
    2. Batch generationAgentConfiguration（ 10-20indivual）
    3. Generate platform configuration
    """
    
    #  
    MAX_CONTEXT_LENGTH = 50000
    #  Agentquantity
    AGENTS_PER_BATCH = 15
    
    #  （ ）
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # Time configuration
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # event configuration
    ENTITY_SUMMARY_LENGTH = 300          # Entity summary
    AGENT_SUMMARY_LENGTH = 300           # Agent 
    ENTITIES_PER_TYPE_DISPLAY = 20       #  
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY Not configured")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
         （ ）
        
        Args:
            simulation_id: simulationID
            project_id: projectID
            graph_id: AtlasID
            simulation_requirement: Simulation requirement description
            document_text: Original document content
            entities:  
            enable_twitter: Whether to enableTwitter
            enable_reddit: Whether to enableReddit
            progress_callback: Progress callback function(current_step, total_steps, message)
            
        Returns:
            SimulationParameters:  
        """
        logger.info(f" : simulation_id={simulation_id},  ={len(entities)}")
        
        #  
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # Time configuration + event configuration + N Agent + Platform configuration
        current_step = 0
        
        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")
        
        # 1.  
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )
        
        reasoning_parts = []
        
        # ========== step1: Build time configuration ==========
        report_progress(1, t('progress.generatingTimeConfig'))
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"{t('progress.timeConfigLabel')}: {time_config_result.get('reasoning', t('common.success'))}")
        
        # ========== step2: Generate event configuration ==========
        report_progress(2, t('progress.generatingEventConfig'))
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"{t('progress.eventConfigLabel')}: {event_config_result.get('reasoning', t('common.success'))}")
        
        # ========== step3-N: Batch generationAgentConfiguration ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]
            
            report_progress(
                3 + batch_idx,
                t('progress.generatingAgentConfig', start=start_idx + 1, end=end_idx, total=len(entities))
            )
            
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement
            )
            all_agent_configs.extend(batch_configs)
        
        reasoning_parts.append(t('progress.agentConfigResult', count=len(all_agent_configs)))
        
        # ==========   Agent ==========
        logger.info("Assign the appropriate publisher to the initial post Agent...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(t('progress.postAssignResult', count=assigned_count))
        
        # ==========  : Generate platform configuration ==========
        report_progress(total_steps, t('progress.generatingPlatformConfig'))
        twitter_config = None
        reddit_config = None
        
        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )
        
        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )
        
        #  
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )
        
        logger.info(f" : {len(params.agent_configs)} indivualAgentConfiguration")
        
        return params
    
    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """buildLLM ， """
        
        # Entity summary
        entity_summary = self._summarize_entities(entities)
        
        #  
        context_parts = [
            f"## Simulation requirements\n{simulation_requirement}",
            f"\n##   ({len(entities)}indivual)\n{entity_summary}",
        ]
        
        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  #  500 
        
        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...( )"
            context_parts.append(f"\n## Original document content\n{doc_text}")
        
        return "\n".join(context_parts)
    
    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """ """
        lines = []
        
        #  
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)
        
        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)}indivual)")
            #  
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ...   {len(type_entities) - display_count} indivual")
        
        return "\n".join(lines)
    
    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """ LLMcall，IncludeJSON """
        import re
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # Lower the temperature each time you retry
                    #  max_tokens，letLLMfree play
                )
                
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # Check if truncated
                if finish_reason == 'length':
                    logger.warning(f"LLMOutput is truncated (attempt {attempt+1})")
                    content = self._fix_truncated_json(content)
                
                # try to parseJSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSONParsing failed (attempt {attempt+1}): {str(e)[:80]}")
                    
                    # try to fixJSON
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    
                    last_error = e
                    
            except Exception as e:
                logger.warning(f"LLMcall failed (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_error or Exception("LLMcall failed")
    
    def _fix_truncated_json(self, content: str) -> str:
        """fix truncatedJSON"""
        content = content.strip()
        
        # Count unclosed parentheses
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # Check if there is an unclosed string
        if content and content[-1] not in '",}]':
            content += '"'
        
        # closing bracket
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """ JSON"""
        import re
        
        #  
        content = self._fix_truncated_json(content)
        
        #  JSON 
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            #  
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)
            
            try:
                return json.loads(json_str)
            except:
                #  
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass
        
        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """Build time configuration"""
        # Truncate length using configured context
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]
        
        #  （80%ofagentnumber）
        max_agents_allowed = max(1, int(num_entities * 0.9))
        
        prompt = f"""Based on the following simulation requirements， 。

{context_truncated}

## Task
 JSON。

###  （ ， ）：
-  ， (UTC+8) 
-  0-5 （activity coefficient0.05）
-  6-8 （activity coefficient0.4）
- working hours9-18 （activity coefficient0.7）
- evening19-22 （activity coefficient1.5）
- 23 （activity coefficient0.5）
-  ： 、 、Moderate working hours、evening peak
- **important**： ， 、 
  - For example： 21-23point； ； 
  - For example： ，off_peak_hours  

### returnJSONFormat（dont wantmarkdown）

 ：
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": " "
}}

 ：
- total_simulation_hours (int): Total simulation time，24-168Hour， 、 
- minutes_per_round (int):  ，30-120minute， 60minute
- agents_per_hour_min (int):  Agentnumber（Value range: 1-{max_agents_allowed}）
- agents_per_hour_max (int):  Agentnumber（Value range: 1-{max_agents_allowed}）
- peak_hours (intarray): peak hours， 
- off_peak_hours (intarray): Trough period， 
- morning_hours (intarray): morning session
- work_hours (intarray): working hours
- reasoning (string):  """

        system_prompt = " 。Return pureJSONFormat， 。"
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}"

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Time configurationLLMBuild failed: {e}, Use default configuration")
            return self._get_default_time_config(num_entities)
    
    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """ （Chinese peoples daily routine）"""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  #  1Hour，Speed ​​up the flow of time
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": " （ 1Hour）"
        }
    
    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """ ， agents_per_hour agentnumber"""
        #  
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))
        
        #  ： agentnumber
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min})  Agentnumber ({num_entities})， ")
            agents_per_hour_min = max(1, num_entities // 10)
        
        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max})  Agentnumber ({num_entities})， ")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)
        
        # make sure min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max，  {agents_per_hour_min}")
        
        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 72),
            minutes_per_round=result.get("minutes_per_round", 60),  #  1Hour
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,  # Almost no one in the early morning
            morning_hours=result.get("morning_hours", [6, 7, 8]),
            morning_activity_multiplier=0.4,
            work_hours=result.get("work_hours", list(range(9, 19))),
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """Generate event configuration"""
        
        #  ，for LLM  
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))
        
        #  
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # Truncate length using configured context
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f"""Based on the following simulation requirements，Generate event configuration。

Simulation requirements: {simulation_requirement}

{context_truncated}

##  
{type_info}

## Task
 JSON：
-  
-  
-  ，**  poster_type（ ）**

**important**: poster_type  " " ，  Agent release。
For example：  Official/University  ，  MediaOutlet release，  Student release。

returnJSONFormat（dont wantmarkdown）：
{{
    "hot_topics": [" 1", " 2", ...],
    "narrative_direction": "< >",
    "initial_posts": [
        {{"content": " ", "poster_type": "Entity type（ ）"}},
        ...
    ],
    "reasoning": "< >"
}}"""

        system_prompt = " 。Return pureJSONFormat。Notice poster_type  。"
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}\nIMPORTANT: The 'poster_type' field value MUST be in English PascalCase exactly matching the available entity types. Only 'content', 'narrative_direction', 'hot_topics' and 'reasoning' fields should use the specified language."

        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"event configurationLLMBuild failed: {e}, Use default configuration")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "Use default configuration"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """ """
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
        Assign the appropriate publisher to the initial post Agent
        
          poster_type   agent_id
        """
        if not event_config.initial_posts:
            return event_config
        
        #   agent  
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        #  （  LLM  ）
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        #   agent  ，  agent
        used_indices: Dict[str, int] = {}
        
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")
            
            #   agent
            matched_agent_id = None
            
            # 1.  
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2.  
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break
            
            # 3.  ，Use the most influential agent
            if matched_agent_id is None:
                logger.warning(f"  '{poster_type}'   Agent，Use the most influential Agent")
                if agent_configs:
                    #  ， 
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0
            
            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id
            })
            
            logger.info(f" : poster_type='{poster_type}' -> agent_id={matched_agent_id}")
        
        event_config.initial_posts = updated_posts
        return event_config
    
    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str
    ) -> List[AgentActivityConfig]:
        """Batch generationAgentConfiguration"""
        
        #  （ ）
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[:summary_len] if e.summary else ""
            })
        
        prompt = f""" ， 。

Simulation requirements: {simulation_requirement}

## Entity list
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## Task
 ，Notice：
- ** **： （ ）， 
- **official agency**（University/GovernmentAgency）： (0.1-0.3)，working hours(9-17) ， (60-240minute)，High influence(2.5-3.0)
- **media**（MediaOutlet）：Active(0.4-0.6)，All day activities(8-23)， (5-30minute)，High influence(2.0-2.5)
- ** **（Student/Person/Alumni）： (0.6-0.9)， (18-23)， (1-15minute)， (0.8-1.2)
- **public figure/ **：Active(0.4-0.6)， (1.5-2.0)

returnJSONFormat（dont wantmarkdown）：
{{
    "agent_configs": [
        {{
            "agent_id": < >,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <Posting frequency>,
            "comments_per_hour": < >,
            "active_hours": [< ， >],
            "response_delay_min": < >,
            "response_delay_max": < >,
            "sentiment_bias": <-1.0arrive1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <influence weight>
        }},
        ...
    ]
}}"""

        system_prompt = " 。Return pureJSON， 。"
        system_prompt = f"{system_prompt}\n\n{get_language_instruction()}\nIMPORTANT: The 'stance' field value MUST be one of the English strings: 'supportive', 'opposing', 'neutral', 'observer'. All JSON field names and numeric values must remain unchanged. Only natural language text fields should use the specified language."

        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent LLMBuild failed: {e}, Generate using rules")
            llm_configs = {}
        
        # buildAgentActivityConfigobject
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # ifLLM ，Generate using rules
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=cfg.get("active_hours", list(range(9, 23))),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0)
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """ AgentConfiguration（Chinese peoples daily routine）"""
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        
        if entity_type in ["university", "governmentagency", "ngo"]:
            # official agency： ， ，high impact
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),  # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # media：All day activities，medium frequency，high impact
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),  # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            #  / ： + ，medium frequency
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),  # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # student：Mainly in the evening， 
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  #  +evening
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            #  ：Mainly in the evening
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  #  +evening
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            #  ：evening peak
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  #  +evening
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
    

