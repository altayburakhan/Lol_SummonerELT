from google.cloud import bigquery
from google.oauth2 import service_account

def cleanup_tables():
    """List and delete all tables in the BigQuery dataset"""
    project_id = "lolelt"
    credentials_path = ".credentials.json"
    
    # Kimlik bilgilerini yükle
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/bigquery"]
    )
    
    # BigQuery istemcisini oluştur
    client = bigquery.Client(
        credentials=credentials,
        project=project_id
    )
    
    # Dataset'i al
    dataset_id = f"{project_id}.lolelt"
    try:
        dataset = client.get_dataset(dataset_id)
    except Exception as e:
        print(f"Dataset bulunamadı, yeni oluşturuluyor: {dataset_id}")
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        dataset = client.create_dataset(dataset, exists_ok=True)
        return
    
    # Tabloları listele
    tables = list(client.list_tables(dataset))
    if not tables:
        print("Dataset boş, silinecek tablo yok.")
        return
        
    print("\nMevcut tablolar:")
    for table in tables:
        print(f"- {table.table_id}")
        
    # Onay al
    confirmation = input("\nBu tabloları silmek istediğinize emin misiniz? (evet/hayır): ")
    if confirmation.lower() != "evet":
        print("İşlem iptal edildi.")
        return
        
    # Tabloları sil
    print("\nTablolar siliniyor...")
    for table in tables:
        client.delete_table(f"{dataset_id}.{table.table_id}")
        print(f"✓ {table.table_id} silindi")
    
    print("\nTüm tablolar başarıyla silindi!")

if __name__ == "__main__":
    cleanup_tables() 