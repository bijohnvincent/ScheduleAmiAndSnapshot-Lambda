#Import modules
import boto3
import datetime
import re

# Initialize global variables
now = datetime.datetime.now()
today = now.day
currentHour = now.hour
currentMonth = now.strftime('%B')
currentWeek = now.strftime('%A')
currentWeekShort = now.strftime('%a')
allowdWeekDayValues=['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat','sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

#Function for creating AMI.   
def createAmi():
    print "Today's is %s  %s %s and current UTC hour is %s" %(currentMonth, today, currentWeek, currentHour)
    ec2 =  boto3.client('ec2')
    Reservations = ec2.describe_instances(Filters=[{'Name':'tag-key','Values':['CreateAmiBackup']}])   # Get details of instances with tag=CreateAmiBackup
    for Instances in Reservations['Reservations']:
        for Instance in Instances['Instances']:
            
            # Initialize variables for each iteration 
            InstanceId = Instance['InstanceId']                                  # Get instance ID for creating AMI and initialize following variables for each instances
            print InstanceId
            AmiFlag = ''
            ExcludedDevices = []
            TransferAmiFlag = ''
            ExcludedDevicesList = []
            SkipAmi = False
            AmiDate = 1                                                          # Default date of AMI if no date is specified
            AmiTime = 0                                                          # Default time of AMI if no time is specified

            for tag in Instance['Tags']:                                         # Get required tag values and transform

                # Check if 'CreateAmiBackup' flag is set.
                # If not, set 'SkipAmi' flag to cancel AMI creation
                if tag['Key'] == 'CreateAmiBackup':
                    print "CreateAmiBackup"
                    CreateAmiFlag = tag['Value'].replace(' ', '').lower()        # Remove whitespaces and convert to lower case
                    if CreateAmiFlag not in ['y', 'yes', 't', 'true', '1']:      # Exit processing remaining Tags if AMI backup is not set
                        SkipAmi = True
                        break
                    
                    
                # Check if 'AmiBackupDates' date is today (UTC)
                # If not, set 'SkipAmi' flag to cancel AMI creation
                elif tag['Key'] == 'AmiBackupDates':
                    print "AmiBackupDates"
                    AmiDateList = tag['Value'].replace(' ', '').rstrip(',').split(",") # Remove unwanted white scpaces and comas and create a list
                    for date in AmiDateList:                                     # Overwrite default value of AMI date with Tag value
                        #print date
                        if date.isalpha():
                            if date.lower() == 'daily':
                                AmiDate = today
                                break
                            elif date.lower() in allowdWeekDayValues:
                                if date.lower() == currentWeek.lower() or currentWeekShort.lower():
                                    AmiDate = today
                                    break
                            else:
                                print "Error: Wrong date entry:"+ date + ". Please correct Tag value. Expecting value Daily/[sun-sat]/[Sunday-Saturday]/[1-31] "
                                continue
                        elif not date.isdigit() or int(date) > 31:                 # Ami date validation
                            print "Error: Wrong date entry:"+ date + ". Please correct Tag value. Expecting value [1-31]/Daily/[sun-sat]/[Sunday-Saturday]"
                            continue
                        if date == str(today):
                            AmiDate = today
                            break
                    if AmiDate != today:                                         
                        SkipAmi = True
                        break                                                    # Exit processing remaining tags if AMI date is not today
                
                
                # Check if 'BackupWindowUTC' tag has UTC current hour
                # If not, set 'SkipAmi' flag to cancel AMI creation
                elif tag['Key'] == 'BackupWindowUTC':
                    print "BackupWindowUTC"
                    AmiTimeList = tag['Value'].replace(' ', '').rstrip(',').split(",")
                    for time in AmiTimeList:                                     # Overwrite default value of AMI time with Tag value
                        print time
                        if not time.isdigit() or int(time) >23:                  # Ami Time validation
                            print "Error: Wrong time entry:"+ time + ". Please correct Tag value. Expecting value [0-23]."
                            continue
                        if int(time) == currentHour:
                            AmiTime = currentHour
                            break
                    if AmiTime != currentHour:
                        SkipAmi = True
                        break                                                    # Exit processing remaining tags if AMI time is not current hour
                
                # Get name of the instance. AMI name will be based on this.    
                elif tag['Key'] == 'Name':
                    InstanceName = tag['Value']
                
                # Get excluded devices from tag 'ExcludeDevices'
                # If there is any error in specified device names, no devices will be exccluded
                elif tag['Key'] == 'ExcludeDevices':
                    print 'ExcludeDevices'
                    ExcludedDevices = tag['Value'].replace(' ', '').rstrip(',').split(',')   # Remove unwanted whitespace and coma and make it a list
                    for device in ExcludedDevices:                               # Loop for creating Exclusion device list
                        if re.match('^/dev/sd[b-z]$', device):                    # Validation for device name
                            ExcludedDevicesList.append({'DeviceName': device, 'NoDevice':'' })  # create list of excluded devices
                        else:
                            print "Error:Wrong device name given for exclusion. It should be in the format: /dev/sd[b-z]  . Will not exclude any devices"
                            ExcludedDevicesList = []
                            print ExcludedDevicesList
                            break
                        print ExcludedDevicesList
                        
                # Check if the 'TransferAmi' flag is set
                #elif tag['Key'] == 'TransferAmi':
                #    TransferAmiFlag = tag['Value'].replace(' ', '').lower()      # Remove whitespaces and convert to lower case
            print AmiDate
            print AmiTime
            if SkipAmi:
                print "Not creating AMI of instance: " + InstanceId
                break
            print "creating AMI of :" + InstanceId
#            if CreateAmiFlag in ['y', 'yes', 't', 'true', '1']:
            print "Creating AMI of Instance ID: %s, Sever Name: %s" %(InstanceId, InstanceName)
            Description = "Created by AWS Lambda AMI Backup Script from %s on %s" %(InstanceId, str(now.isoformat()))
            AmiName = InstanceName + now.strftime(" - AMI taken on %Y-%m-%d at %H.%M.%S")
            print AmiName
            print ExcludedDevicesList
            AmiResponse = ec2.create_image(DryRun=False,
                                        InstanceId=InstanceId,
                                        Name=AmiName,
                                        Description=Description,
                                        NoReboot=True,
                                        BlockDeviceMappings=ExcludedDevicesList
                                      )
            AmiId = AmiResponse['ImageId']
            if AmiResponse['ResponseMetadata']['HTTPStatusCode'] == 200:
                print "HTTPStatusCode=200. Successfully created AMI: " + AmiId
            AmiTags = [tag for tag in Instance['Tags'] if (tag['Key'] != 'CreateAmiBackup') and (tag['Key'] != 'TransferAmi') and (tag['Key'] != 'AmiBackupDates') and  (tag['Key'] != 'BackupWindowUTC')]   # Remove unwanted tags from the Tag list.
            ec2.create_tags(Resources=[AmiId], Tags=AmiTags)                 # Tag new AMI
    return
            
'''            
            ImageDetails = ec2.describe_images(DryRun=False, ImageIds=[AmiId])
            DeviceMappings = ImageDetails['Images'][0]['BlockDeviceMappings']
            SnapshotIds = []
            for device in DeviceMappings:
                SnapshotIds.append(device['Ebs']['SnapshotId'])
            for SnapshotId in SnapshotIds:
               ec2.create_tags(Resources=[SnapshotId], Tags=AmiTags)        # Tag new Snapshots created as part of new AMI
''' 
    

# Main Function
def ami_backup(json_val, context):
    createAmi()