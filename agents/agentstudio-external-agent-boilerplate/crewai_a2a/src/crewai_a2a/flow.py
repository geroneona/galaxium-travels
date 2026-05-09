#!/usr/bin/env python
# Allow protected access for CrewAILLM helper used to extract response text
# pylint: disable=protected-access

import json
import traceback
from pydantic import BaseModel
from agentstudio_sdk.hooks import use_hook_context
from agentstudio_sdk.llm import LLM, Provider, CrewAILLM
from crewai.flow.flow import Flow, listen, start, router
from crewai import Crew, Task
from crewai_a2a.agents import weather_agent, food_agent, term_reader_agent, term_writer_agent


class BoilerplateState(BaseModel):
    user_input: str = ""
    topic: str = ""
    answer: str = ""


class ClassificationResult(BaseModel):
    answer: str = ""
    topic: str = ""


class BoilerplateFlow(Flow[BoilerplateState]):
    """Boilerplate flow that demonstrates a routing to specialized agents based on user input."""

    @start()
    async def classify_user_input(self):
        """Get input from the user"""
        with use_hook_context(agent_name="CrewAIClassifier"):
            try:
                # Get user input
                if not self.state.user_input:
                    self.state.user_input = input("Waiting for input...")

                # Initialize custom LLM with ICA discovery (uses Provider.azure with fallback to ICA)
                raw_llm = LLM(provider=Provider.azure, model="gpt-4o")
                crew_llm = CrewAILLM(raw_llm)

                await crew_llm.init()

                # Build classification prompt for JSON response
                prompt = f"""You are an intent classifier. Categorize user messages and route to the appropriate agent.
Given the user's message, match to one of these topics:
    - weather: for questions related to the weather
    - food: for questions related to food, cooking, recipes, etc.
    - term-reader: for questions about retrieving, viewing, listing, or getting business term definitions
    - term-writer: for questions about creating, adding, or writing new business term definitions
If unrelated to these topics, respond with topic="null".

Respond in JSON format: {{"topic": "...", "answer": "..."}}

User message: "{self.state.user_input}"
"""

                response_obj = await crew_llm.generate(prompt)

                # Extract text from raw Bedrock response via CrewAILLM
                response_text = crew_llm._extract_text_from_response(response_obj)
                print(f"DEBUG classify: response_text={response_text}")

                # Parse response - handle JSON in code blocks
                try:
                    # Remove markdown code blocks if present
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        response_text = response_text.split("```")[1].split("```")[0].strip()

                    response_data = json.loads(response_text)
                    topic = response_data.get("topic", "null")
                    answer = response_data.get("answer", "")
                    print(f"DEBUG classify: parsed topic={topic}, answer={answer}")
                except Exception as e:
                    print(f"DEBUG classify: JSON parse error: {e}")
                    topic = "null"
                    answer = response_text

                if topic == "null":
                    # Only set answer if no valid topic was found
                    self.state.answer = answer
                    print("DEBUG classify: No valid topic, returning answer")
                    return self.state

                # Valid topic found - clear answer and set topic for routing
                # The answer will be set by the agent that handles this topic
                self.state.answer = ""
                self.state.topic = topic
                print(f"DEBUG classify: Set state.topic={self.state.topic}")
                # Don't return anything here - let the flow continue to the router
                return self.state

            except Exception as e:
                print(f"Error in classify_user_input: {e}")
                print(traceback.format_exc())
                raise

    @router(classify_user_input)
    def topic_router(self):
        """Route to the appropriate agent based on topic"""
        print(f"DEBUG topic_router: topic={self.state.topic}")
        # Return the topic directly - CrewAI will match this to @listen() conditions
        topic = self.state.topic
        print(f"DEBUG topic_router: returning {topic}")
        return topic

    @listen("weather")
    def weather_advice(self):
        """provide weather advice"""
        with use_hook_context(agent_name="WeatherAgent"):
            print(f"DEBUG weather_advice: topic={self.state.topic}")
            try:
                # Create a task for the weather agent
                task = Task(
                    description=f"Provide weather information based on the user's request: {self.state.user_input}",
                    expected_output="Weather information and advice",
                    agent=weather_agent,
                )

                # Create and execute the crew
                crew = Crew(agents=[weather_agent], tasks=[task], verbose=True)

                result = crew.kickoff()
                self.state.answer = str(result)
                return self.state.answer
            except Exception as e:
                print(f"Error in weather_advice: {e}")
                print(traceback.format_exc())
                raise

    @listen("food")
    def food_advice(self):
        """provide food advice"""
        with use_hook_context(agent_name="MealAgent"):
            print(f"DEBUG food_advice: topic={self.state.topic}")
            try:
                # Create a task for the food agent
                task = Task(
                    description=f"Provide food and meal information based on the user's request: {self.state.user_input}",
                    expected_output="Food and meal advice",
                    agent=food_agent,
                )

                # Create and execute the crew
                crew = Crew(agents=[food_agent], tasks=[task], verbose=True)

                result = crew.kickoff()
                self.state.answer = str(result)
                return self.state.answer
            except Exception as e:
                print(f"Error in food_advice: {e}")
                print(traceback.format_exc())
                raise

    @listen("term-reader")
    def term_reader_advice(self):
        """provide term reading advice"""
        with use_hook_context(agent_name="Term Reader Agent"):
            print(f"DEBUG term_reader_advice: topic={self.state.topic}, executing crew")
            try:
                # Create a task for the term reader agent
                task = Task(
                    description=f"""Retrieve business term definitions based on the user's request: {self.state.user_input}
                
                CRITICAL INSTRUCTIONS:
                - You must use the GET/read MCP tool to retrieve existing terms (read-only operation)
                - Call the MCP tool with EMPTY parameters {{}} to list all available terms
                - Do NOT use any CREATE, POST, or WRITE operations
                - Present the retrieved terms in a clear, user-friendly format
                - If no terms are found, inform the user that the glossary is empty""",
                    expected_output="A list of business terms with their definitions from the Rulebook AI glossary",
                    agent=term_reader_agent,
                )

                # Create and execute the crew
                crew = Crew(agents=[term_reader_agent], tasks=[task], verbose=True)

                result = crew.kickoff()
                self.state.answer = str(result)
                return self.state.answer
            except Exception as e:
                print(f"Error in term_reader_advice: {e}")
                print(traceback.format_exc())
                raise

    @listen("term-writer")
    def term_writer_advice(self):
        """provide term writing advice"""
        with use_hook_context(agent_name="Term Writer Agent"):
            print(f"DEBUG term_writer_advice: topic={self.state.topic}")
            try:
                # Create a task for the term writer agent
                task = Task(
                    description=f"Create new business term definitions based on the user's request: {self.state.user_input}",
                    expected_output="Confirmation of the newly created business term in the Rulebook AI glossary",
                    agent=term_writer_agent,
                )

                # Create and execute the crew
                crew = Crew(agents=[term_writer_agent], tasks=[task], verbose=True)

                result = crew.kickoff()
                self.state.answer = str(result)
                return self.state.answer
            except Exception as e:
                print(f"Error in term_writer_advice: {e}")
                print(traceback.format_exc())
                raise


def plot():
    """Generate a visualization of the flow"""
    flow = BoilerplateFlow()
    flow.plot("guide_creator_flow")
    print("Flow visualization saved to guide_creator_flow.html")
