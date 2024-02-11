import os
import sys

from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import TextLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.vectorstores import Chroma
from main import get_travel_plan_details
from parse import parse_flight_details_from_soap_response

import constants

os.environ["OPENAI_API_KEY"] = constants.APIKEY

# Enable to save to disk & reuse the model (for repeated queries on the same data)
PERSIST = False

# Get user input for travel plans
user_input = input("Please describe your travel plans: ")

# Get SOAP API response using the refactored function
soap_response_data = get_travel_plan_details(user_input)

# Parse flight details from SOAP response
flight_details = parse_flight_details_from_soap_response(soap_response_data)

# Initialize query variable for the loop
query = None

# Setup index creation and retrieval chain
if PERSIST and os.path.exists("persist"):
    print("Reusing index...\n")
    vectorstore = Chroma(persist_directory="persist")
    index = VectorstoreIndexCreator(vectorstore=vectorstore)
else:
    # Save the SOAP response data to a temporary file for loading
    temp_data_file_path = "temp_data.txt"
    with open(temp_data_file_path, "w") as file:
        file.write(soap_response_data)
    loader = TextLoader(temp_data_file_path)  # Use this line if you only need temp_data.txt
    # loader = DirectoryLoader("data/")  # Use this line if you have a data directory
    if PERSIST:
        index = VectorstoreIndexCreator(vectorstore_kwargs={"persist_directory": "persist"}).from_loaders([loader])
    else:
        index = VectorstoreIndexCreator().from_loaders([loader])

chain = ConversationalRetrievalChain.from_llm(
    llm=ChatOpenAI(model="gpt-3.5-turbo"),
    retriever=index.vectorstore.as_retriever(search_kwargs={"k": 1}),
)

chat_history = []
while True:
    if not query:
        query = input("Prompt: ")
    if query in ['quit', 'q', 'exit']:
        sys.exit()
    if 'flight' in query.lower():
        print("Here are the flight details:")
        for passenger, details in flight_details.items():
            print(f"Passenger: {passenger}")
            print(f"Departure City: {details['departure_city']}")
            print(f"Arrival City: {details['arrival_city']}")
            print(f"Departure Date: {details['departure_date']}")
            print(f"Departure Time: {details['departure_time']}")
            print(f"Arrival Date: {details['arrival_date']}")
            print(f"Arrival Time: {details['arrival_time']}")
            print(f"Price: {details['price']}")
            print()
    else:
        result = chain({"question": query, "chat_history": chat_history})
        print(result['answer'])

        chat_history.append((query, result['answer']))
    query = None
