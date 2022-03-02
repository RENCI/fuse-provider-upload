#
#   prove -v t/write.t [ :: [--verbose] [--dry_run] ]
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

use Test::More tests => 4;
use Test::File::Contents;

use lib './t';
use Support;

our $verbose = 0;
our $dry_run = 0;

our $OBJID="test_object_id";
our $SUBMITTER_ID='test@email.com';
our $ACCESSID="None";
our $PASSPORTS='["foo" "bar"]';


# read the .env file
use Dotenv;      
Dotenv->load;

our $HOST_PATH = "http://localhost:$ENV{'API_PORT'}";

GetOptions('dry_run' => \$dry_run,
	   'verbose' => \$verbose) or die "Usage: prove -v t/$0 [ :: [--verbose] ] \n";
if($verbose){
    print("+ dry_run: $dry_run\n");
    print("+ verbose: $verbose\n");
    print("+ API_PORT: $ENV{'API_PORT'}\n");
}

my $fn ;

cleanup_out();

$fn = "write-1.json";
files_eq(f($fn), cmd("POST", $fn, "submit?submitter_id=${SUBMITTER_ID}&requested_object_id=${OBJID}","-F 'client_file=@./t/input/test_upload.tz;type=application/x-zip-compressed' -H 'Content-Type: multipart/form-data'"),
	                                                                                                   "Submit an object");
$fn = "write-2.json";
files_eq(f($fn), cmd("GET",$fn, "search/{$SUBMITTER_ID}"),                                                 "Get list of objects submitted by $SUBMITTER_ID");
# In a typical use case, never delete data; see documentation
$fn = "write-3.json";
files_eq(f($fn), cmd("DELETE", $fn, "delete/${OBJID}"),                                                    "Delete a the downloaded groupid (status=deleted)");
$fn = "write-4.json";
generalize_output($fn, cmd("DELETE", rawf($fn), "delete/${OBJID}"), ["stderr"]);
files_eq(f($fn), "t/out/${fn}",                                                                            "Delete a the downloaded groupid (status=exception)");
