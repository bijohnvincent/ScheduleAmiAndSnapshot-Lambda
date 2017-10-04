# Name          : AmiRetention
# Author        : Bijohn Vincent
# Functionality : This script will delete the AMI and it's associated snapshots once it 
#                   is older than the retention period set.
# File version  : 1.1
#

# Import required modules.
import boto3
import datetime

# Get current time (UTC)
now = datetime.datetime.now()

# Function for deleting old AMIs.
def deregisterOldAmis():
    print now
    ec2 =  boto3.client('ec2')
    Amis = ec2.describe_images(Filters=[{'Name':'description','Values':['Created by AWS Lambda AMI Backup*']}])
    for ami in Amis['Images']:
        #print ami


        # Initialize the default value for AMI retention in case no override value is set in tags
        # Get the AMI retention override value.
        # If there is a override value in tag, set it as retenion period
        
        amiRetention = 7 # default retention period of AMIs created by Lambda Backup Script. In days
        for tag in ami['Tags']:
            if tag['Key'] == 'AmiRetentionDays':
                if not tag['Value'].isdigit():
                    print "Value set for tag AmiRetentionDays =", tag['Value'], "is Invalid. Using default retention"
                    amiRetentionOverride = False
                    break
                amiRetentionOverride = tag['Value']
                break
            else:
                amiRetentionOverride = False
        if amiRetentionOverride:
            amiRetention = int(amiRetentionOverride)
            
            
        amiCreationDate= datetime.datetime.strptime(ami['CreationDate'], "%Y-%m-%dT%H:%M:%S.%fZ")
        amiAge = now - amiCreationDate
        if amiAge > datetime.timedelta(days = amiRetention):
            
            # Get details of snapshots attached with this AMI. 
            ImageDetails = ec2.describe_images(DryRun=False, ImageIds=[ami['ImageId']])
            DeviceMappings = ImageDetails['Images'][0]['BlockDeviceMappings']
            SnapshotIds = []
            for device in DeviceMappings:
                if "Ebs" not in device:       # Skip if the device is not an EBS volume
                    continue
                SnapshotIds.append(device['Ebs']['SnapshotId'])

            # Deregister AMI 
            print "AMI %s is %s hour old. Retention is set as %s days. Deleting %s." % (ami['ImageId'], amiAge, amiRetention, ami['ImageId'])
            ec2.deregister_image(DryRun=False, ImageId=ami['ImageId'])
            
            # Delete snapshots of this AMI
            for SnapshotId in SnapshotIds:
               print "Deleting ", SnapshotId
               ec2.delete_snapshot(DryRun=False, SnapshotId=SnapshotId)
            
        else:
            print "AMI %s is %s hour old. Retention is set as %s days. Doing nothing." % (ami['ImageId'], amiAge, amiRetention,)
    return


# Main function
def deregister_ami(event, context):
    deregisterOldAmis()
