#
#   prove -v t/DRS.t [ :: [--verbose] [--dry_run] ]
#
# Assumes containers are built and running (use up.sh)
#
# Dependencies:
#   jq
# To install:
#   cpan App::cpanminus
#   # restart shell, then get the dependencies:
#   cpanm --installdeps .
# For more details:
#   http://www.cpan.org/modules/INSTALL.html

use 5.16.3;
use strict;
use warnings;

use Getopt::Long qw(GetOptions);

use Test::More tests => 14;
use Test::File::Contents;

use lib './t';
use Support;

our $verbose = 0;
our $dry_run = 0;

our $OBJID="test_object_id";
our $OBJID2="test_csv_object_id";
our $SUBMITTER_ID='test-xxx@email.com';
our $ACCESSID="None";
our $PASSPORTS='["foo" "bar"]';


# read the .env file
use Dotenv;      
Dotenv->load;

our $HOST_PATH = "http://localhost:$ENV{'HOST_PORT'}";


GetOptions('dry_run' => \$dry_run,
	   'verbose' => \$verbose) or die "Usage: prove -v t/$0 [ :: [--verbose] ] \n";
if($verbose){
    print("+ dry_run: $dry_run\n");
    print("+ verbose: $verbose\n");
    print("+ HOST_PORT: $ENV{'HOST_PORT'}\n");
}

my $fn ;

cleanup_out();

$fn = "DRS-1.json";
generalize_output($fn, cmd("GET", rawf($fn), "service-info"), ["createdAt", "updatedAt"]);
files_eq(f($fn), "t/out/${fn}",                                                    "($fn) Get config for this service");

$fn = "write-1.json";
files_eq(f($fn), cmd("POST", $fn, "submit?submitter_id=${SUBMITTER_ID}&requested_object_id=${OBJID}&data_type=dataset-geneExpression&version=1.0",
		     "-F 'client_file=@./t/input/for-testing.zip;type=application/zip' -H 'Content-Type: multipart/form-data' -H 'accept: application/json'"),
	                                                                                                   "($fn) Submit zip file");

$fn = "write-1b.json";
files_eq(f($fn), cmd("POST", $fn, "submit?submitter_id=${SUBMITTER_ID}&requested_object_id=${OBJID2}&data_type=dataset-geneExpression&version=1.0",
		     "-F 'client_file=@./t/input/phenotypes.csv;type=application/csv' -H 'Content-Type: multipart/form-data' -H 'accept: application/json'"),
	                                                                                                   "($fn) Submit csv file");

$fn = "DRS-2.json";
generalize_output($fn, cmd("GET", rawf($fn), "objects/{$OBJID}"), ["created_time", "updated_time"]);
files_eq(f($fn), "t/out/${fn}",                                                                            "($fn) Get info about zip DRS object");

$fn = "DRS-2b.json";
generalize_output($fn, cmd("GET", rawf($fn), "objects/{$OBJID2}"), ["created_time", "updated_time"]);
files_eq(f($fn), "t/out/${fn}",                                                                            "($fn) Get info about csv DRS object");

$fn = "DRS-3.empty";
files_eq(f($fn), cmd("GET",$fn, "files/${OBJID}", "--output t/out/for-testing.zip"),                       "($fn) Get the zip'd file");
files_eq("t/input/for-testing.zip", "t/out/for-testing.zip",                                               "Ensure retrieved zip'd file is correct");

$fn = "DRS-3b.empty";
files_eq(f($fn), cmd("GET",$fn, "files/${OBJID2}", "--output t/out/phenotypes.csv"),                       "($fn) Get the csv file");
files_eq("t/input/phenotypes.csv", "t/out/phenotypes.csv",                                                 "Ensure retrieved csv file is correct");

$fn = "write-2.json";
files_eq(f($fn), cmd("GET",$fn, "search/{$SUBMITTER_ID}"),                                                 "($fn) Get list of objects submitted by $SUBMITTER_ID");

# In a typical use case, never delete data; see documentation
$fn = "write-3.json";
files_eq(f($fn), cmd("DELETE", $fn, "delete/${OBJID}"),                                                    "($fn) Delete the zip'd object (status=deleted)");
$fn = "write-3b.json";
files_eq(f($fn), cmd("DELETE", $fn, "delete/${OBJID2}"),                                                   "($fn) Delete the csv object (status=deleted)");
$fn = "write-4.json";
generalize_output($fn, cmd("DELETE", rawf($fn), "delete/${OBJID}"), ["stderr"]);
files_eq(f($fn), "t/out/${fn}",                                                                            "($fn) Delete the zip'd object again (status=exception)");
$fn = "write-4b.json";
generalize_output($fn, cmd("DELETE", rawf($fn), "delete/${OBJID2}"), ["stderr"]);
files_eq(f($fn), "t/out/${fn}",                                                                            "($fn) Delete the csv object again (status=exception)");



#$fn = "DRS-3.json";
#generalize_output($fn, cmd("POST", rawf($fn), "objects/{$OBJID}", "-d '$PASSPORTS'"), ["created_time", "updated_time"]);
#files_eq(f($fn), "t/out/${fn}",                                                     "Get info about DRS object through POST-ing a Passport");
#$fn = "DRS-4.json";
#files_eq(f($fn), cmd("GET",$fn, "objects/{$OBJID}/access/{$ACCESSID}"),             "Get URL for fetching bytes");
#$fn = "DRS-5.json";
#files_eq(f($fn), cmd("GET",$fn, "objects/{$OBJID}/access/{$ACCESSID}", $PASSPORTS), "Get URL for fetching bytes through POST-ing a Passport");

