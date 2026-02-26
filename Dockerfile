# FROM baseimage: baseimage is a starting point
FROM python:3.12-slim
# python:3.12-slim as baseimage

# change directory to app directory
WORKDIR /app

# copy requirements.txt file
COPY requirements.txt ./

# install app dependencies
RUN pip install -r requirements.txt
#  RUN is used while building the container

# copy code into the image
COPY . .

# run the app
CMD ["uvicorn", "chatbot:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD is used to START the container AFTER building
# there can be only 1 CMD command in a dockerfile
