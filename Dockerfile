# Use Python 3.9
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy your code
COPY . .

# Hugging Face Spaces require port 7860
EXPOSE 7860

# Start the server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]