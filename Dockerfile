# Use the official Python image
FROM python:3.13

# Set the working directory
WORKDIR /code

# Copy the requirements file into the image
COPY requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy all files in the current directory into the image
COPY . /code

# Expose the port the app runs on
EXPOSE 80

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]