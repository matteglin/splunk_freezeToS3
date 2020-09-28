import logging
import boto3
import re
import os, sys
import splunk.clilib.cli_common
from botocore.exceptions import ClientError

S3_BUCKET = "meglin-test-bucket"

def freeze_bucket(bucket_path, instanceGuid):
	for subdir, dirs, files in os.walk(bucket_path):
		for file in files:
			#print Path
			#print(os.path.join(subdir, file))
			bucket_path = os.path.join(subdir, file)
			index_name = index_name_from_bucket_path(bucket_path)
		
			path_match = re.search(r'(?<='+index_name+').*', bucket_path)
			bucket_pathing = path_match.group(0)
		
			# TODO: HACK - need to reconcile on-disk path segment with index config...
			if index_name == "defaultdb":
				index_name = "main"
			if index_name == "_internaldb":
				index_name = "_internal"
			if index_name == "audit":
				index_name = "_audit"
		
			s3_dest_path = instanceGuid + "/" + index_name + bucket_pathing
			#print("Index : %s" % index_name)
			#print("Destination Path : %s" % s3_dest_path)
			upload_file(os.path.join(subdir, file),S3_BUCKET,s3_dest_path)

def index_name_from_bucket_path(path):
	#indexName = os.path.basename(os.path.dirname(os.path.dirname(path)))
	#path_match = re.search(r'\/([\w-]+)(?:\/[\w]+\/db_)', path)
	path_match = re.search(r'([^\/]+)\/[\w]+\/(?:(?:db)|(?:rb))_', path)
	indexName = path_match.group(1)  
	return indexName

def get_instance_guid():
    instanceCfg = splunk.clilib.cli_common.readConfFile(
            os.path.join(splunk.clilib.cli_common.splunk_home, "etc", "instance.cfg"))
    return instanceCfg["general"]["guid"]

def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True
    
    
def main(args):
    if 2 != len(args):
        raise Exception, "Expected 1 param (bucket path)."
    buckPath = args[1]
    #buckOwnerList = os.path.join(splunk.clilib.cli_common.splunk_home,
    #        "bucket_owners.json")
    instanceGuid = get_instance_guid()
    #if do_i_own_bucket(buckOwnerList, buckPath, instanceGuid):
    freeze_bucket(buckPath, instanceGuid)
    # Return value not necessary.  If the bucket list contained the to-be-frozen
    # bucket in question, then we've done one of a few things:
    # 1) Uploaded bucket to S3 successfuly.  We will return exitcode 0 and Splunk
    #    will delete the bucket.
    # 2) We do not own this bucket, so will not upload (avoid uploads of
    #    replicated buckets).  We still return exitcode 0 so our Splunk instance
    #    will delete the bucket -- here we are relying on another Splunk
    #    instance to own the bucket and do the upload.
    # 3) The bucket in question did not exist in the list at all, meaning it is
    #    unknown to the presumed universe of Splunk indexers - since nobody will
    #    be able to claim ownership of the bucket and perform the upload/freeze,
    #    all instances of this script should throw an exception -- in other
    #    words, return non-zero, so the calling Splunk instance will refuse to
    #    delete the bucket.  This allows for cleaning up the mess at a later
    #    time without losing the data in this bucket.

if __name__ == "__main__":
    main(sys.argv)