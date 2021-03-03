import json, boto3, os, datetime

def write_to_S3(file_data, bucket, key):
    s3_client = boto3.client('s3')
    return s3_client.put_object(
        Body=str(json.dumps(file_data)),
        Bucket=bucket,
        Key=key)

def get_time_stamp():
    parser = datetime.datetime.now() 
    return parser.strftime("%d-%m-%Y_%H_%M_%S")

def lambda_handler(event, context):
    
    # Setup the boto3 clients for the API calls
    ssm = boto3.client('ssm')

    bucket = os.environ['OUTPUT_BUCKET']

    # Not sure why this is here? - chrisj
    # get_inventory = ssm.get_paginator('get_inventory')
    # response_iterator = get_inventory.paginate()

    # Initiate the response dictionary
    response = {}

    # Set default filter
    instanceFilter = {'Key': 'PlatformTypes','Values': ['Windows']}
    
    # Append instance Ids to filter if provided in request payload
    if 'instanceIds' in event:
        instanceFilter.update({'Key': 'InstanceIds', 'Values': event['instanceIds']})
    
    server_paginator = ssm.get_paginator('describe_instance_information')
    get_servers = server_paginator.paginate(
        Filters=[
            instanceFilter
        ],
        MaxResults = 50
        )
    
    for page in get_servers:
        for instance in page['InstanceInformationList']:
            
            # Fix up the datetimeobjects so that we can dump these out to JSON later
            try:
                instance['LastPingDateTime'] = instance['LastPingDateTime'].strftime('%m/%d/%Y %H:%M:%S')
            except KeyError:
                pass
            
            try:
                instance['RegistrationDate'] = instance['RegistrationDate'].strftime('%m/%d/%Y %H:%M:%S')
            except KeyError:
                pass
            
            try:
                instance['LastAssociationExecutionDate'] = instance['LastAssociationExecutionDate'].strftime('%m/%d/%Y %H:%M:%S')
            except KeyError:
                pass
            
            try:    
                instance['LastSuccessfulAssociationExecutionDate'] = instance['LastSuccessfulAssociationExecutionDate'].strftime('%m/%d/%Y %H:%M:%S')
            except KeyError:
                pass
            
            inventory = ssm.list_inventory_entries(
               InstanceId = instance["InstanceId"],
               TypeName = "AWS:Application",
               MaxResults = 50
            )
            
            inv_list = inventory
            
            # Loop through pages using NextToken to read next page
            while inventory.get("NextToken"):
                Token = inventory.get("NextToken")
                inventory.pop("NextToken") # Without pop we'll have infinate loop :)
                inventory = ssm.list_inventory_entries(
                    InstanceId = instance["InstanceId"],
                    TypeName = "AWS:Application",
                    NextToken= Token
                    )
                inv_list["Entries"].extend(inventory["Entries"])
            
            instance["inventory"] = inv_list
            
            response[instance['ComputerName']] = instance
    output_file = f'{get_time_stamp()}.txt'
    s3response = write_to_S3(response, bucket, output_file)

    print(s3response)
    print(json.dumps(response))
    return f'https://s3.console.aws.amazon.com/s3/object/{bucket}?region=ap-southeast-2&prefix={output_file}'