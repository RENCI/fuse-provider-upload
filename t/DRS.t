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

use Test::More tests => 5;
use Test::File::Contents;

use lib './t';
use Support;

our $verbose = 0;
our $dry_run = 0;

our $OBJID="test_object_id";
our $ACCESSID="None";
our $PASSPORTS='["foo" "bar"]';


# read the .env file
use Dotenv;      
Dotenv->load;

our $HOST_PATH = "http://localhost:$ENV{'API_PORT'}"; #8082;


GetOptions('dry_run' => \$dry_run,
	   'verbose' => \$verbose) or die "Usage: prove -v t/$0 [ :: [--verbose] ] \n";
if($verbose){
    print("+ dry_run: $dry_run\n");
    print("+ verbose: $verbose\n");
    print("+ API_PORT: $ENV{'API_PORT'}\n");
}

my $fn ;

cleanup_out();

$fn = "DRS-1.json";
generalize_output($fn, cmd("GET", rawf($fn), "service-info"), ["createdAt", "updatedAt"]);
files_eq(f($fn), "t/out/${fn}",                                                    "Get config for this service");
$fn = "DRS-2.json";
generalize_output($fn, cmd("GET", rawf($fn), "objects/{$OBJID}"), ["created_time", "updated_time"]);
files_eq(f($fn), "t/out/${fn}",                                                    "Get info about DRS object");
$fn = "DRS-3.json";
generalize_output($fn, cmd("POST", rawf($fn), "objects/{$OBJID}", $PASSPORTS), ["created_time", "updated_time"]);
files_eq(f($fn), "t/out/${fn}",                                                     "Get info about DRS object through POST-ing a Passport");
$fn = "DRS-4.json";
files_eq(f($fn), cmd("GET",$fn, "objects/{$OBJID}/access/{$ACCESSID}"),             "Get URL for fetching bytes");
$fn = "DRS-5.json";
files_eq(f($fn), cmd("GET",$fn, "objects/{$OBJID}/access/{$ACCESSID}", $PASSPORTS), "Get URL for fetching bytes through POST-ing a Passport");

