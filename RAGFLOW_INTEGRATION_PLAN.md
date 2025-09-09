AGENT MANAGEMENT

List agents

RAGFlow.list_agents(
    page: int = 1, 
    page_size: int = 30, 
    orderby: str = "create_time", 
    desc: bool = True,
    id: str = None,
    title: str = None
) -> List[Agent]

Lists agents.

Parameters

page: int

Specifies the page on which the agents will be displayed. Defaults to 1.

page_size: int

The number of agents on each page. Defaults to 30.

orderby: str

The attribute by which the results are sorted. Available options:

"create_time" (default)
"update_time"
desc: bool

Indicates whether the retrieved agents should be sorted in descending order. Defaults to True.

id: str

The ID of the agent to retrieve. Defaults to None.

name: str

The name of the agent to retrieve. Defaults to None.

Returns

Success: A list of Agent objects.
Failure: Exception.
Examples

from ragflow_sdk import RAGFlow
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
for agent in rag_object.list_agents():
    print(agent)

Create agent

RAGFlow.create_agent(
    title: str,
    dsl: dict,
    description: str | None = None
) -> None

Create an agent.

Parameters

title: str

Specifies the title of the agent.

dsl: dict

Specifies the canvas DSL of the agent.

description: str

The description of the agent. Defaults to None.

Returns

Success: Nothing.
Failure: Exception.
Examples

from ragflow_sdk import RAGFlow
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
rag_object.create_agent(
  title="Test Agent",
  description="A test agent",
  dsl={
    # ... canvas DSL here ...
  }
)

Update agent

RAGFlow.update_agent(
    agent_id: str,
    title: str | None = None,
    description: str | None = None,
    dsl: dict | None = None
) -> None

Update an agent.

Parameters

agent_id: str

Specifies the id of the agent to be updated.

title: str

Specifies the new title of the agent. None if you do not want to update this.

dsl: dict

Specifies the new canvas DSL of the agent. None if you do not want to update this.

description: str

The new description of the agent. None if you do not want to update this.

Returns

Success: Nothing.
Failure: Exception.
Examples

from ragflow_sdk import RAGFlow
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
rag_object.update_agent(
  agent_id="58af890a2a8911f0a71a11b922ed82d6",
  title="Test Agent",
  description="A test agent",
  dsl={
    # ... canvas DSL here ...
  }
)

Delete agent

RAGFlow.delete_agent(
    agent_id: str
) -> None

Delete an agent.

Parameters

agent_id: str

Specifies the id of the agent to be deleted.

Returns

Success: Nothing.
Failure: Exception.
Examples

from ragflow_sdk import RAGFlow
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
rag_object.delete_agent("58af890a2a8911f0a71a11b922ed82d6")



Create session with agent

Agent.create_session(**kwargs) -> Session

Creates a session with the current agent.

Parameters

**kwargs

The parameters in begin component.

Returns

Success: A Session object containing the following attributes:
id: str The auto-generated unique identifier of the created session.
message: list[Message] The messages of the created session assistant. Default: [{"role": "assistant", "content": "Hi! I am your assistant, can I help you?"}]
agent_id: str The ID of the associated agent.
Failure: Exception
Examples

from ragflow_sdk import RAGFlow, Agent

rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
agent_id = "AGENT_ID"
agent = rag_object.list_agents(id = agent_id)[0]
session = agent.create_session()

Converse with agent

Session.ask(question: str="", stream: bool = False) -> Optional[Message, iter[Message]]

Asks a specified agent a question to start an AI-powered conversation.

NOTE
In streaming mode, not all responses include a reference, as this depends on the system's judgement.
Parameters

question: str

The question to start an AI-powered conversation. Ifthe Begin component takes parameters, a question is not required.

stream: bool

Indicates whether to output responses in a streaming way:

True: Enable streaming (default).
False: Disable streaming.
Returns

A Message object containing the response to the question if stream is set to False
An iterator containing multiple message objects (iter[Message]) if stream is set to True
The following shows the attributes of a Message object:

id: str

The auto-generated message ID.

content: str

The content of the message. Defaults to "Hi! I am your assistant, can I help you?".

reference: list[Chunk]

A list of Chunk objects representing references to the message, each containing the following attributes:

id str
The chunk ID.
content str
The content of the chunk.
image_id str
The ID of the snapshot of the chunk. Applicable only when the source of the chunk is an image, PPT, PPTX, or PDF file.
document_id str
The ID of the referenced document.
document_name str
The name of the referenced document.
position list[str]
The location information of the chunk within the referenced document.
dataset_id str
The ID of the dataset to which the referenced document belongs.
similarity float
A composite similarity score of the chunk ranging from 0 to 1, with a higher value indicating greater similarity. It is the weighted sum of vector_similarity and term_similarity.
vector_similarity float
A vector similarity score of the chunk ranging from 0 to 1, with a higher value indicating greater similarity between vector embeddings.
term_similarity float
A keyword similarity score of the chunk ranging from 0 to 1, with a higher value indicating greater similarity between keywords.
Examples

from ragflow_sdk import RAGFlow, Agent

rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
AGENT_id = "AGENT_ID"
agent = rag_object.list_agents(id = AGENT_id)[0]
session = agent.create_session()    

print("\n===== Miss R ====\n")
print("Hello. What can I do for you?")

while True:
    question = input("\n===== User ====\n> ")
    print("\n==== Miss R ====\n")
    
    cont = ""
    for ans in session.ask(question, stream=True):
        print(ans.content[len(cont):], end='', flush=True)
        cont = ans.content

List agent sessions

Agent.list_sessions(
    page: int = 1, 
    page_size: int = 30, 
    orderby: str = "update_time", 
    desc: bool = True,
    id: str = None
) -> List[Session]

Lists sessions associated with the current agent.

Parameters

page: int

Specifies the page on which the sessions will be displayed. Defaults to 1.

page_size: int

The number of sessions on each page. Defaults to 30.

orderby: str

The field by which sessions should be sorted. Available options:

"create_time"
"update_time"(default)
desc: bool

Indicates whether the retrieved sessions should be sorted in descending order. Defaults to True.

id: str

The ID of the agent session to retrieve. Defaults to None.

Returns

Success: A list of Session objects associated with the current agent.
Failure: Exception.
Examples

from ragflow_sdk import RAGFlow

rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
AGENT_id = "AGENT_ID"
agent = rag_object.list_agents(id = AGENT_id)[0]
sessons = agent.list_sessions()
for session in sessions:
    print(session)

Delete agent's sessions

Agent.delete_sessions(ids: list[str] = None)

Deletes sessions of a agent by ID.

Parameters

ids: list[str]

The IDs of the sessions to delete. Defaults to None. If it is not specified, all sessions associated with the agent will be deleted.

Returns

Success: No value is returned.
Failure: Exception
Examples

from ragflow_sdk import RAGFlow

rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
AGENT_id = "AGENT_ID"
agent = rag_object.list_agents(id = AGENT_id)[0]
agent.delete_sessions(ids=["id_1","id_2"])