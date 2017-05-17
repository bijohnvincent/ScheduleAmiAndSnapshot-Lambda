
# Name          : SnapshotRetention
# Author        : Bijohn Vincent
# Functionality : This script will remove the snapshots that are created Ebs backup script in this project.
#                   Default retention day is set as 7 days. You can override it by adding a tag 'SnapshotRetentionDays'
#                   on your EBS volume which will be couped to the new snapshot by EBS backup script in this project.
#                   


# Import modules
import boto3
import datetime


# Function for deleting old snapshots.
def deleteOldSnapshot():
    now = datetime.datetime.now()
    ec2 =  boto3.client('ec2')
    Snapshots = ec2.describe_snapshots(Filters=[{'Name':'description','Values':['Created by AWS Lambda Backup Script*']}])
    for snapshot in Snapshots['Snapshots']:
        snapshotRetention = 7 # Retention period of snapshots, created by Lambda Backup Script. In days
        for tag in snapshot['Tags']:    # Get the snapshot retention override value
            if tag['Key'] == 'SnapshotRetentionDays':
                if not tag['Value'].isdigit():
                    print "Value set for tag SnapshotRetentionDays =", tag['Value'], "is Invalid. Using default retention"
                    snapshotRetentionOverride = False
                    break
                snapshotRetentionOverride = tag['Value']
                break
            else:
                snapshotRetentionOverride = False
        if snapshotRetentionOverride:
            snapshotRetention = int(snapshotRetentionOverride)
        snapshotAge = now - snapshot['StartTime'].replace(tzinfo=None)
        print now, snapshot['StartTime'], snapshot['StartTime'].replace(tzinfo=None)
        if snapshotAge > datetime.timedelta(days = snapshotRetention):
            print "Snapshot %s is %s hour old. Retention is set as %s days. Deleting %s." % (snapshot['SnapshotId'], snapshotAge, snapshotRetention, snapshot['SnapshotId'])
            ec2.delete_snapshot(DryRun=False, SnapshotId=snapshot['SnapshotId'])
        else:
            print "Snapshot %s is %s hour old. Retention is set as %s days. Doing nothing." % (snapshot['SnapshotId'], snapshotAge, snapshotRetention,)
    return

# Main Function
def remove_snapshot(json_val, context):
    deleteOldSnapshot()
