from influxdb_client import InfluxDBClient

url = "http://influxdb:8086"
token = "hasuighduisaghaduigcui"
org = "S4T"
bucket_name = "clear_communication"

client = InfluxDBClient(url=url, token=token, org=org)
buckets_api = client.buckets_api()
buckets_api.create_bucket(bucket_name=bucket_name, org=org)
print(f"Bucket {bucket_name} created.")
