import requests
import io

def download_file_from_google_drive(id, destination=None):
    #URL = "https://drive.google.com/file/d/1CUz1Ksp_1dKBBF3uv8AvWaYE4nbmOjzd/view"
    #https://drive.google.com/u/0/uc?id=1CUz1Ksp_1dKBBF3uv8AvWaYE4nbmOjzd&export=download
    URL = "https://docs.google.com/uc"

    with requests.Session() as session:
        with session.get(URL,  params={"id": id}, stream = True) as response:
            if destination!=None:
                save_response_content_to_file(response, destination)
            else:
                return save_response_content_to_buffer(response)

def save_response_content_to_buffer(response):
    CHUNK_SIZE = 32768
    buffer = io.BytesIO()
    for chunk in response.iter_content(CHUNK_SIZE):
        if chunk: 
            buffer.write(chunk)
    buffer.seek(0)
    return buffer



def save_response_content_to_file(response, destination):
    CHUNK_SIZE = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                f.write(chunk)

if __name__ == "__main__":
    file_id = '1CUz1Ksp_1dKBBF3uv8AvWaYE4nbmOjzd'
    destination = 'test.file.png'
    # buffer = download_file_from_google_drive(file_id, destination=None)
    # print(buffer)
    # with open("test.png", "wb") as f:
    #     f.write(buffer.getbuffer())