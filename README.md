Internet In A Box
=================

2013

*THIS PROJECT IS UNDER HEAVY INITIAL CONSTRUCTION*
Please come back in a few weeks. :)


Abstract
--------

The Internet-in-a-Box is a small, inexpensive device which provides essential
Internet resources without any Internet connection.  It provides a local copy
of half a terabyte of the world's Free information.

An Internet-in-a-Box provides:

- *Wikipedia*: Complete Wikipedia in a dozen different languages
- *Maps*: Zoomable world-wide maps down to street level
- *E-books*: Over 35 thousand e-books in a variety of languages
- *Software*: Huge library of Open Source Software, including installable Ubuntu Linux OS with all software package repositories.  Includes full source code for study or modification.
- *Video*: Hundreds of hours of instructional videos
- *Chat*: Simple instant messaging across the community


OpenStreetMap
-------------

We are installing on an Ubuntu 12.04 quad-core 3GHz machine with
16 GB RAM and a 500GB SSD.

You must have a beefy machine.  Note that on an quad-core 8GB RAM
2.5GHz machine the planet import time was TWO WEEKS!

More detailed instructions are available from the switch2osm.org project.  However they have you build all tools from source:
http://switch2osm.org/serving-tiles/manually-building-a-tile-server-12-04/


1. Download Planet File

Download the latest OSM Planet file.  Use the newer "pbf" format (which is
binary), and not the "bz2" format (which is XML).

The latest planet.osm.pbf.torrent can be downloaded via bittorrent from:
http://osm-torrent.torres.voyager.hr/files/planet-latest.osm.pbf.torrent

planet.osm.pbf is about 20 GB in size.



2. Install OSM Software

    add-apt-repository ppa:kakrueger/openstreetmap
    apt-get update
    apt-get remove --purge postgresql-9.1-postgis postgresql-client-9.1 postgresql-client-common postgresql-common
    apt-get install libapache2-mod-tile osm2pgsql openstreetmap-postgis-db-setup
    dpkg-reconfigure openstreetmap-postgis-db-setup


Not sure how much of the following is actually required:

    sudo apt-get install subversion git-core tar unzip wget bzip2 build-essential autoconf libtool libxml2-dev libgeos-dev libpq-dev libbz2-dev proj munin-node munin libprotobuf-c0-dev protobuf-c-compiler libfreetype6-dev libpng12-dev libtiff4-dev libicu-dev libboost-all-dev libgdal-dev libcairo-dev libcairomm-1.0-dev apache2 apache2-dev libagg-dev

(Make sure to install from ppa:kakrueger and not the outdated
versions in the main Ubuntu repositories or things will be bad)

    osm2pgsql -v
    osm2pgsql SVN version 0.81.0


3. Prepare a swap file on the SSD

Create a 16 GB swap file on the SSD.

    dd if=/dev/zero of=/mnt/ssd/swapfile bs=1024 count=16000000
    mkswap -L ssdswap /mnt/ssd/swapfile
Add line to /etc/fstab, and comment out existing swap
    /mnt/ssd/swapfile none            swap    sw              0       0
Activate swap
    swapoff -a  # Turn off existing swap
    swapon -a  # Turn on new SSD swap


4. Wipe out old Postgres database and move it to SSD

We are going to wipe the old Postgres directory and start from
scratch with a directory on our SSD.  It is possible to do
incremental updates to the OSM database, but we haven't tried it.

    /etc/init.d/postgresql stop
    mv -v /var/lib/postgresql /mnt/ssd/
    ln -s /mnt/ssd/postgresql /var/lib/postgresql
    /etc/init.d/postgresql start


5. Setup the OSM Postgres/PostGIS database

    sudo -u postgres -i
    createuser braddock # answer yes for superuser (although this isn't strictly necessary)
    createdb -E UTF8 -O braddock gis
    psql -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql -d gis
    psql -d gis -c "ALTER TABLE geometry_columns OWNER TO braddock; ALTER TABLE spatial_ref_sys OWNER TO braddock;"
    exit


6. Tune Postgresql

See section "Tuning your system" in http://switch2osm.org/serving-tiles/manually-building-a-tile-server/ 


6. Import planet (will takes days)

    time osm2pgsql --slim -C 14000 planet-130206.osm.pbf

NOTE: Consider using --number-processes 4 next time!

See the performance (and options) of others at:
http://wiki.openstreetmap.org/wiki/Osm2pgsql/benchmarks

Note you can get statistics on number of nodes, ways, and relations at:
http://www.openstreetmap.org/stats/data_stats.html

Wikipedia
---------

This section describes how to make a complete Mediawiki-based Wikipedia mirror
for many languages.  This is not necessary if you are using kiwix - see the
section on Kiwiz ZIM File Download instead.

Install:
    apt-get install mysql-server php5 apache2 php5-mysql

First relocate the mysql directory.
    mv /var/lib/mysql /var/lib/mysql.orig
    ln -s /knowledge/processed/mysql /var/lib/mysql

Had to inform AppArmor of the new path (make sure there are no symlinks, or
modify this to provide a full path).
    cat >>/etc/apparmor.d/local/usr.sbin.mysqld  <<EOF
    /knowledge/processed/mysql rwk,
    /knowledge/processed/mysql/** rwk,
    EOF

Use wp-download to download the latest wikipedia dumps for various languages.
There is a wpdownloadrc config file in Heritage/wpdownloadrc

    Edit wpdownloadrc to comment out languages you don't want
    pip install wp-download
    wp-download -c wpdownloadrc /knowledge/data/wikipedia/dumps

Once downloaded, you need to import the wikipedia dump data into mysql
databases and mediawiki installations.  To do this use Heritage/scripts/make_wiki.py 

    sudo scripts/make_wiki.py -p mypassword -r rootpassword ar fr ru vi zh

By default, this script will look for wikipedia dumps as organized by
wp-download in /knowledge/data/wikipedia/dumps and select the latest downloaded
dump for each language specified on the command line.  It will create mysql
databases for each language.  It will create a stand-alone mediawiki
installation under /knowledge/processed/wiki/, which should be linked from
/var/www/wiki for proper operation.

    ln -s /knowledge/processed/wiki /var/www/wiki

After this is complete your new wikis should be accessible at http://localhost/wiki/arwiki (for example)


Kiwix ZIM File Download
-----------------------

1. Install Firefox plugin "Download Them All"
2. http://www.kiwix.org/index.php/Template:ZIMdumps
3. Tools->Download Them All->DownloadThemAll
4. In DTA dialog, open "Fast Filtering"
5. Enter Fast Filter "*.zim.torrent"
6. Start!
7. mv ~/Downloads/*.zim.torrent /knowledge/data/zim/torrents/
8. Open Transmission Bitorrent client
9. Open -> select all *.zim.torrent in file dialog
10. Select download destination /knowledge/data/zim/downloads/


Ubuntu Software Repository
--------------------------

    apt-get install apt-mirror
    apt-mirror scripts/mirror.list
(will mirror into /knowledge/data/ubuntu/12.04)


Project Gutenberg Mirror
------------------------

    cd /knowledge/data/gutenberg  (?)
    while (true); do (date; . ../../Heritage/rsync_gutenberg; sleep 3600) | tee -a 20120823.log; done


Khan Academy
------------

For the latest torrent, see the newest comments on the official Khan Academy issue ticket:

    http://code.google.com/p/khanacademy/issues/detail?id=191

As of 3/17/2013 the lastest most complete torrent by Zurd is at:

    http://www.legittorrents.info/index.php?page=torrent-details&id=f388128c5f528d248235b4c7b67eb81c3804eb43

Install some codec dependencies (Ubuntu 12.04):

    sudo -E wget --output-document=/etc/apt/sources.list.d/medibuntu.list http://www.medibuntu.org/sources.list.d/$(lsb_release -cs).list && sudo apt-get --quiet update && sudo apt-get --yes --quiet --allow-unauthenticated install medibuntu-keyring && sudo apt-get --quiet update
    apt-get install ffmpeg libfaac0 libavcodec-extra-53 libx264-120

Convert webm to a more mobile friendly format:

    scripts/video_convert.py --extension .webm --threads 4 /knowledge/data/khanacademy.org/Khan\ Academy/ /knowledge/processed/Khan\ Academy

video_convert.py is designed to be run efficiently on multiple NFS-mounted computers simultaneously in parallel.

(this takes approximately 20 hours on two four-core CPUs)


Web Service
-----------

    cd internet-in-a-box
    pip install Flask-Babel whoosh Flask-SQLAlchemy
    ./run.py

----
