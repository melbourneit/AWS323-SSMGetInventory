import json, boto3

def lambda_handler(event, context):
    
    # Setup the boto3 clients for the API calls
    ssm = boto3.client('ssm')
    get_inventory = ssm.get_paginator('get_inventory')
    response_iterator = get_inventory.paginate()
    
    # Initiate the response dictionary
    response = {}
    
    # Iterate through the get inventory API, gives us the inventory list of all the applications for each amanged instance. Will almost always give paginated results so built that in here
    # TODO: probably need to add TypeName is as an environment variable
    for page in response_iterator:
        for each in page['Entities']:
            inventory = ssm.list_inventory_entries(
                InstanceId = each['Id'],
                TypeName = "AWS:Application"
                )
            
            # Inventory API doesn't return the ComputerName; so let's go get that to make it more user friendly
            servernameresponse = ssm.describe_instance_information(
                    Filters=[
                        {'Key': 'InstanceIds','Values': [each['Id']]},
                        ]
                )
            
            # Assign server name as ComputerName if it's available, otherwise leave it as the instanceid
            # TODO: Work out why a registered instance wouldn't returna  result from the describe instance api
            try:
                servername = servernameresponse['InstanceInformationList'][0]['ComputerName']
            except IndexError:
                servername = each['Id']
            
            # Loop through the application inventory and add it to the response list along with the servername
            for application in inventory['Entries']:
                if response.get(application['Name']) is None:
                    response.update({application['Name'] : [servername]})
                else:
                    response[application['Name']] += [servername]
                    
    print(response)