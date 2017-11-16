#!/usr/bin/python
# --------------------------------------------------------------------------------------------------
# Create AWS AMI from Instance and delete old AMI
# Script looking for tag Name with value "SERVER_NAME"
# Author: Denis Astahov
#
# Version      Date           Name                Info
# 1.0          02-Nov-2017    Denis Astahov       Initial Version
#
# --------------------------------------------------------------------------------------------------
"""   This Policy need to be added into ROLE for EC2 Instance
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1426256275000",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateSnapshot",
                "ec2:CreateTags",
                "ec2:DeleteSnapshot",
                "ec2:DescribeSnapshots",
                "ec2:DescribeVolumes",
                "ec2:DescribeInstances",
                "ec2:DescribeImages",
                "ec2:CreateSnapshot",
                "ec2:CreateImage",
                "ec2:DeregisterImage"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
"""
import boto3, time, os

AWS_DEFAULT_REGION = "us-west-2"                                 # Region where server running
	
DAYS = 7                                      # Days for AMI to keep, older will be deleted
SERVER_NAME = "MyWebServer"                   # Name of EC2 to look for for creating AMI
NEWAMI_NAME = ""                              # Name of new AMI and SNAPHOTS saved here (SERVER_NAME + Time) don not touch! :)


def get_instanceid(server_name):
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances( Filters=[
	                                             { 'Name': 'tag-key',             'Values' : ['Name']},
                                                 { 'Name': 'tag-value',           'Values' : [server_name]},
                                                 { 'Name': 'instance-state-name', 'Values' : ['running']}
                                               ])
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            return instance_id


def create_ami(instance_id):
    global SERVER_NAME
    global NEWAMI_NAME
    ec2 = boto3.client('ec2')
    amitime = str(time.strftime('-%d%b%Y-%H-%M', time.gmtime(time.time())))
    NEWAMI_NAME = SERVER_NAME + amitime
    response = ec2.create_image(
        InstanceId= instance_id,
        Name= NEWAMI_NAME,
        NoReboot=True
    )
    new_ami_id = response['ImageId']   # Save New ami_id
    return new_ami_id

def create_tags_on(new_ami_id):
    global SERVER_NAME
    global NEWAMI_NAME
    ec2 = boto3.client('ec2')
    print("Adding NAME TAG: [" + SERVER_NAME + "] to:")
    print("\t" + new_ami_id)

    ec2.create_tags(                        # Add TAG to AMI
        Resources=[ new_ami_id ],
        Tags=[
            {
                'Key': 'Name',
                'Value': SERVER_NAME
            },
        ]
    )

    disks=[]  # List of Snapshots attached to AMI
    response = ec2.describe_images(ImageIds = [new_ami_id])
    for image in response["Images"]:
        for snaphsot in image["BlockDeviceMappings"]:
            disks.append(snaphsot['Ebs']['SnapshotId'])    # Save Snaphots ID to Disk List

    for disk in disks:
        print("Adding NAME TAG: [" + NEWAMI_NAME + "] to:")
        print("\t" + disk)
        ec2.create_tags(                         # Add TAG to SNAPHOTS
            Resources=[disk],
            Tags=[
                {
                    'Key': 'Name',
                    'Value': NEWAMI_NAME
                },
            ]
        )



def delete_old_ami(DAYS, ami_tagname ):
    ec2 = boto3.client('ec2')

    nowTime = time.time()  # Get Current Time    in Seconds
    ageTime = nowTime - 60 * 60 * 24 * DAYS  # Get X days old Time in Seconds
    ami_list = []  # List of AMI with TAG 'ami_tagname'
    response = ec2.describe_images(Filters=[
                                            {'Name': 'tag-key',   'Values': ['Name']},
                                            {'Name': 'tag-value', 'Values': [ami_tagname]}
                                           ])
    if len(response['Images']) == 0:  # if no AMI found with this name
        print("No AMI found with name: " + ami_tagname)
        exit(1)
    else:
        ami_list = response['Images']  # Save List of Images
        #newest_date = max(date['CreationDate'] for date in ami_list)  # Get Newest CreationDate
        print("Total AMIs found: " + str(len(response['Images'])))
        for x in ami_list:
            currentAMIID = x['ImageId']
            mytime = x['CreationDate']
            mytime = mytime.replace('T',' ')
            mytime = mytime[:-5]
            mytime = time.strptime(mytime, "%Y-%m-%d %H:%M:%S")
            creationTimeinSeconds = time.mktime(mytime)
            disks = []  # List of Snapshots attached to AMI which we need to delete
            if ageTime > creationTimeinSeconds:   # Deregister AMI and Delete Snaphosts
                response = ec2.describe_images(ImageIds=[currentAMIID])
                for image in response["Images"]:
                    for snaphsot in image["BlockDeviceMappings"]:
                        disks.append(snaphsot['Ebs']['SnapshotId'])  # Save Snaphots ID to Disk List
                print("Deleting AMI: " + str(currentAMIID))
                ec2.deregister_image(ImageId=currentAMIID)
                for disk in disks:
                    print("Deleting DISK: " + str(disk))
                    ec2.delete_snapshot(SnapshotId=disk)
            else:
                print(currentAMIID + " - Still not older than " + str(DAYS) + " days.")
					
					
#======================== Script Execution Start Here======================================
print("----------------------------------START--------------------------------------")
os.environ['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION
server_id = get_instanceid(SERVER_NAME)
print("InstanceID: " + server_id)

new_ami_id = create_ami(server_id)
print("Server New AMI ID: " + new_ami_id)
print("Server AMIID Name: " + NEWAMI_NAME)

print ("Waiting 10 sec to let Snapshots start creating... ")
time.sleep(10)
create_tags_on(new_ami_id)

print("Cheking if there are AMI older than " + str(DAYS) + " days...")
delete_old_ami(DAYS, SERVER_NAME )    # Older than XX days , NameTag to look for
print("----------------------------------DONE--------------------------------------")


