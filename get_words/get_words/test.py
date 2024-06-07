import sqlite3
import openai

# OPENAI_API_KEY 설정
OPENAI_API_KEY =  "sk-"
# openai API 키 인증
openai.api_key = OPENAI_API_KEY

def get_hosts_from_db(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT host FROM hosts")
    hosts = cursor.fetchall()
    connection.close()
    return [host[0] for host in hosts]

def get_top10_keywords(db_path, host):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    query = """
    SELECT words FROM words_count 
    WHERE host = ? 
    ORDER BY count DESC 
    LIMIT 10
    """
    cursor.execute(query, (host,))
    top_10_keywords = cursor.fetchall()
    connection.close()
    return [keyword[0] for keyword in top_10_keywords if keyword[0] is not None]

def classify_site(top_10_keywords):
    if not top_10_keywords:
        return "접속 불가 또는 존재하지않음"

    keywords_sentence = ", ".join(top_10_keywords)
    question = f"웹사이트의 top 10 키워드입니다: {keywords_sentence}. 웹사이트가 다음 중 어떤 종류인지 판단해주세요: 도박사이트, 성인사이트, 무료웹툰사이트, 토렌트, 정상. 부연설명은 필요없어."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": question}
        ]
    )
    classification = response.choices[0].message['content'].strip()

    if any(word in classification for word in ["도박사이트", "성인사이트", "무료웹툰사이트", "토렌트", "정상"]):
        return classification
    else:
        return "알 수 없음"

def update_classification_in_db(db_path, host, classification):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("INSERT OR IGNORE INTO hosts (host) VALUES (?)", (host,))
    cursor.execute("UPDATE hosts SET classification = ? WHERE host = ?", (classification, host))
    connection.commit()
    connection.close()

def main():
    db_path = 'word_counts.db'
    hosts = get_hosts_from_db(db_path)
    
    for host in hosts:
        top_10_keywords = get_top10_keywords(db_path, host)
        if not top_10_keywords:
            classification = "접속 불가 또는 존재하지않음"
        else:
            classification = classify_site(top_10_keywords)
        update_classification_in_db(db_path, host, classification)
        print(f"Host: {host} - Classification: {classification}")

if __name__ == "__main__":
    main()
