# Name          : EbsBackup
# Author        : Bijohn Vincent
# Functionality : This script will create snapshot of the EBS volume either by the tags of the volume or by manual invokation.
#               1) Manual invokation will help you to create snapshot of the volume from the ec2 instance. You can invoke this
#                   lambda function programmatically after freezing the filesystem or IO to volume, to ensure consistent snapshot. 
#                   You can pass the volume Ids to this Lambda function as below:
#                    {
#                       "volumeIds": "<volumeId1>[, <volumeId2>, <volumeId3>, ...]>"
#                     }
#               2) Can invoke this function as a scheduled event. For that you can add a comma(,) separated hours as value for
#                   the tag 'BackupWindowUTC'. Optionally you can add a tag 'SnapshotRetentionDays' on volumes for automated 
#                   removal of snapshot created by this script (done by another Lambda function 'remove_snapshot.py' ).
#                   


# Import modules
import boto3
import datetime


#
# Function for creating snapshot by checking volume tags.   
#
def CheckTagsAndCreateSnapshot(ec2,now):

    currentHour= now.hour
    
    # Get details of volumes with tag=BackupWindowUTC
    Volumes = ec2.describe_volumes(Filters=[{'Name':'tag-key','Values':['BackupWindowUTC']}])
    
    # Create snapshot of each volume based on the value on tag
    for vol in Volumes['Volumes']:
        
        # Remove MountPoint and BackupWindowUTC tags from the Tag list. Remaining tags will be applied to new snapshot 
        snapshotTags = [tag for tag in vol['Tags'] if (tag['Key'] != 'MountPoint') and (tag['Key'] != 'BackupWindowUTC') ]
        
        for tag in vol['Tags']:
            if tag['Key'] == 'BackupWindowUTC':
                hourTag = tag['Value'].replace(' ', '')   # remove whitespaces from BackupWindowUTC Tag
                hourList = hourTag.split(",")   # Convert BackupWindowUTC to python list
                
                for hour in hourList:
                    # Check if the hour entry in tag is valid
                    if not hour.isdigit() or int(hour) > 23:
                        print "Value set for tag BackupWindowUTC =", hour, "is Invalid"
                        continue
                    
                    # Create snapshot if current UTC time equals the backup hour in tag
                    if currentHour == int(hour):
                        snapshotDescription = "Created by AWS Lambda Backup Script from %s on %s" %(vol['VolumeId'], str(now.isoformat()))
                        
                        #Create snapshot of the volume
                        snapshotDetails = ec2.create_snapshot(DryRun=False, VolumeId=vol['VolumeId'], Description=snapshotDescription)
                        print "Creating snapshot of %s. SnapshotId=%s." % (vol['VolumeId'], snapshotDetails['SnapshotId'])
                        
                        # Tag new Snapshot and exit parsing current volume tags
                        ec2.create_tags(Resources=[snapshotDetails['SnapshotId']], Tags=snapshotTags)
                        break
                    else:
                        print "Current Hour is %s UTC. Backup window of %s is set as %s. Doing nothing." % (currentHour, vol['VolumeId'], tag['Value'])
    return

#
# This is main function 
#
def ebs_backup(json_val, context):
    ec2 =  boto3.client('ec2')
    # Initialise time
    now = datetime.datetime.now()
    
    # If not invoked by CloudWatch event, process the json input
    if not 'Scheduled Event' in str(json_val):
        print "Manual invocation"
        
        # Validate the input json file and print expected format if the json is in wrong format.
        if not 'volumeIds' in json_val:
            print ''' Wrong input. Expected format:
                   {
                       "volumeIds": "<volumeId1>[, <volumeId2>, <volumeId3>, ...]>"
                   }'''
            return None
        
        # Convert 'volumeIds' in json to python 'list'. Remove unwanted spaces in the list.
        volumeIds=map(str.strip,str(json_val['volumeIds']).split(","))
        
        # Get details of volumes 
        Volumes = ec2.describe_volumes(VolumeIds=volumeIds)
        
        # Take snapshot of each volumes
        for vol in Volumes:
            snapshotDescription = "Created by AWS Lambda Backup Script from %s on %s" %(vol['VolumeId'], str(now.isoformat()))
            
            # Remove MountPoint and BackupWindowUTC tags from the Tag list. Remaining tags will be applied to new snapshot 
            snapshotTags = [tag for tag in vol['Tags'] if (tag['Key'] != 'MountPoint') and (tag['Key'] != 'BackupWindowUTC') ]
            
            #Create snapshot of the volume
            snapshotDetails = ec2.create_snapshot(DryRun=False, VolumeId=vol['VolumeId'], Description=snapshotDescription)
            print "Creating snapshot of %s. SnapshotId=%s." % (vol['VolumeId'], snapshotDetails['SnapshotId'])
                        
            # Tag new Snapshot
            ec2.create_tags(Resources=[snapshotDetails['SnapshotId']], Tags=snapshotTags)

    else:
        print "CloudWatch Scheduled event"
        CheckTagsAndCreateSnapshot(ec2,now)
    return
