import boto3
import datetime

now = datetime.datetime.now()
currentHour= now.hour

# Function for creating snapshot.   
def createSnapshot():
    ec2 =  boto3.client('ec2')
    Volumes = ec2.describe_volumes(Filters=[{'Name':'tag-key','Values':['BackupWindowUTC']}])   # Get details of volumes with tag=BackupWindowUTC
    for vol in Volumes['Volumes']:
        snapshotTags = [tag for tag in vol['Tags'] if (tag['Key'] != 'MountPoint') and (tag['Key'] != 'BackupWindowUTC') ]   # Remove MountPoint and BackupWindowUTC tags from the Tag list.
        for tag in vol['Tags']:
            if tag['Key'] == 'BackupWindowUTC':
                hourTag = tag['Value'].replace(' ', '')   # remove whitespaces from BackupWindowUTC Tag
                hourList = hourTag.split(",")   # Convert BackupWindowUTC to python list
                for hour in hourList:
                    if not hour.isdigit() or int(hour) > 23:
                        print "Value set for tag BackupWindowUTC =", hour, "is Invalid"
                        continue
                    if currentHour == int(hour):  # Create snapshot if current UTC time equals the backup hour
                        snapshotDescription = "Created by AWS Lambda Backup Script from %s on %s" %(vol['VolumeId'], str(now.isoformat()))  
                        snapshotDetails = ec2.create_snapshot(DryRun=False, VolumeId=vol['VolumeId'], Description=snapshotDescription)  #Create snapshot of the volume
                        print "Creating snapshot of %s. SnapshotId=%s." % (vol['VolumeId'], snapshotDetails['SnapshotId'])
                        ec2.create_tags(Resources=[snapshotDetails['SnapshotId']], Tags=snapshotTags)  # Tag new Snapshot
                    else:
                        print "Current Hour is %s UTC. Backup window of %s is set as %s. Doing nothing." % (currentHour, vol['VolumeId'], tag['Value'])
    return

# Main Function
def ebs_backup(json_val, context):
    createSnapshot()