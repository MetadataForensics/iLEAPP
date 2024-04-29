# Photos.sqlite
# Author:  Scott Koenig, assisted by past contributors
# Version: 1.2
#
#   Description:
#   Parses records for different methods which media files have been shared via iCloud Share
#   found in the PhotoData-Photos.sqlite ZSHARE Table and supports iOS 14-17. Parses iCloud Share Methods and
#   Participant records only no asset data being parsed. The iCloud Share methods being stored in these records include
#   Shred iCloud Links Cloud Master Moments-CMM and Shared iCloud Photo Library (SPL).
#   This parser is based on research and SQLite Queries written by Scott Koenig
#   https://theforensicscooter.com/ and queries found at https://github.com/ScottKjr3347
#

import os
from datetime import datetime
import pytz
import json
import shutil
import base64
from PIL import Image
from pillow_heif import register_heif_opener
import glob
import sys
import stat
from pathlib import Path
import sqlite3
import nska_deserialize as nd
import scripts.artifacts.artGlobals
from packaging import version
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, kmlgen, is_platform_windows, media_to_html, open_sqlite_db_readonly


def get_ph30icldsharemethphdapsql(files_found, report_folder, seeker, wrap_text, timezone_offset):
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('.sqlite'):
            break
      
    if report_folder.endswith('/') or report_folder.endswith('\\'):
        report_folder = report_folder[:-1]
    iosversion = scripts.artifacts.artGlobals.versionf
    if version.parse(iosversion) <= version.parse("13.7"):
        logfunc("Unsupported version for PhotoData-Photos.sqlite zSHARE iCloud Shared Method records"
                " with no asset data on iOS " + iosversion)
    if (version.parse(iosversion) >= version.parse("14")) & (version.parse(iosversion) < version.parse("16")):
        file_found = str(files_found[0])
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()

        cursor.execute("""
        SELECT
        DateTime(zShare.ZCREATIONDATE + 978307200, 'UNIXEPOCH') AS 'zShare-Creation Date',
        DateTime(zShare.ZSTARTDATE + 978307200, 'UNIXEPOCH') AS 'zShare-Start Date',
        DateTime(zShare.ZENDDATE + 978307200, 'UNIXEPOCH') AS 'zShare-End Date',
        DateTime(zShare.ZEXPIRYDATE + 978307200, 'UNIXEPOCH') AS 'zShare-Expiry Date',
        zShare.ZUUID AS 'zShare-UUID',
        zShare.ZORIGINATINGSCOPEIDENTIFIER AS 'zShare-Originating Scope ID',
        CASE zShare.ZSTATUS
            WHEN 1 THEN '1-Active_Share-CMM_or_SPL-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSTATUS || ''
        END AS 'zShare-Status',
        CASE zShare.ZSCOPETYPE
            WHEN 2 THEN '2-iCloudLink-CMMoment-2'
            WHEN 4 THEN '4-iCld-Shared-Photo-Library-SPL-4'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSCOPETYPE || ''
        END AS 'zShare-Scope Type',
        zShare.ZASSETCOUNT AS 'zShare-Asset Count',
        zShare.ZFORCESYNCATTEMPTED AS 'zShare-Force Sync Attempted',
        zShare.ZPHOTOSCOUNT AS 'zShare-Photos Count',
        zShare.ZUPLOADEDPHOTOSCOUNT AS 'zShare-Uploaded Photos Count',
        zShare.ZVIDEOSCOUNT AS 'zShare-Videos Count',
        zShare.ZUPLOADEDVIDEOSCOUNT AS 'zShare-Uploaded Videos Count',        
        zShare.ZSCOPEIDENTIFIER AS 'zShare-Scope ID',
        zShare.ZTITLE AS 'zShare-Title-SPL',
        zShare.ZSHAREURL AS 'zShare-Share URL',
        CASE zShare.ZLOCALPUBLISHSTATE
            WHEN 2 THEN '2-Published-2'
            ELSE 'Unknown-New-Value!: ' || zShare.ZLOCALPUBLISHSTATE || ''
        END AS 'zShare-Local Publish State',
        CASE zShare.ZPUBLICPERMISSION
            WHEN 1 THEN '1-Public_Premission_Denied-Private-1'
            WHEN 2 THEN '2-Public_Premission_Granted-Public-2'
            ELSE 'Unknown-New-Value!: ' || zShare.ZPUBLICPERMISSION || ''
        END AS 'zShare-Public Permission',
        CASE zSharePartic.ZACCEPTANCESTATUS
            WHEN 1 THEN '1-Invite-Pending_or_Declined-1'
            WHEN 2 THEN '2-Invite-Accepted-2'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZACCEPTANCESTATUS || ''
        END AS 'zSharePartic-Acceptance Status',
        zSharePartic.ZUSERIDENTIFIER AS 'zSharePartic-User ID',
        zSharePartic.Z_PK AS 'zSharePartic-zPK',
        zSharePartic.ZEMAILADDRESS AS 'zSharePartic-Email Address',
        zSharePartic.ZPHONENUMBER AS 'zSharePartic-Phone Number',
        CASE zSharePartic.ZISCURRENTUSER
            WHEN 0 THEN '0-Participant-Not_CurrentUser-0'
            WHEN 1 THEN '1-Participant-Is_CurrentUser-1'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZISCURRENTUSER || ''
        END AS 'zSharePartic-Is Current User',
        CASE zSharePartic.ZROLE
            WHEN 1 THEN '1-Participant-is-Owner-Role-1'
            WHEN 2 THEN '2-Participant-is-Invitee-Role-2'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZROLE || ''
        END AS 'zSharePartic-Role',
        CASE zSharePartic.ZPERMISSION
            WHEN 3 THEN '3-Participant-has-Full-Premissions-3'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZPERMISSION || ''
        END AS 'zSharePartic-Premission',
        CASE zShare.ZSHOULDNOTIFYONUPLOADCOMPLETION
            WHEN 0 THEN '0-DoNotNotify-SPL-0'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSHOULDNOTIFYONUPLOADCOMPLETION || ''
        END AS 'zShare-Should Notify On Upload Completion',
        CASE zShare.ZSHOULDIGNOREBUDGETS
            WHEN 1 THEN '1-StillTesting-CMM-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSHOULDIGNOREBUDGETS || ''
        END AS 'zShare-Should Ignor Budgets',
        CASE zShare.ZTRASHEDSTATE
            WHEN 0 THEN '0-Not_in_Trash-0'
            WHEN 1 THEN '1-In_Trash-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZTRASHEDSTATE || ''
        END AS 'zShare-Trashed State',
        CASE zShare.ZCLOUDDELETESTATE
            WHEN 0 THEN '0-Not Deleted-0'
            ELSE 'Unknown-New-Value!: ' || zShare.ZCLOUDDELETESTATE || ''
        END AS 'zShare-Cloud Delete State',
        CASE zShare.Z_ENT
            WHEN 55 THEN '55-SPL-Entity-55'
            WHEN 56 THEN '56-CMM-iCloud-Link-Entity-56'
            ELSE 'Unknown-New-Value!: ' || zShare.Z_ENT || ''
        END AS 'zShare-zENT'
        FROM ZSHARE zShare
            LEFT JOIN ZSHAREPARTICIPANT zSharePartic ON zSharePartic.ZSHARE = zShare.Z_PK
        ORDER BY zShare.ZCREATIONDATE
        """)

        all_rows = cursor.fetchall()
        usageentries = len(all_rows)
        data_list = []
        counter = 0
        if usageentries > 0:
            for row in all_rows:
                data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
                                  row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18],
                                  row[19], row[20], row[21], row[22], row[23], row[24], row[25], row[26], row[27],
                                  row[28], row[29], row[30], row[31]))

                counter += 1

            description = 'Parses records for different methods which media files have been shared via iCloud Share' \
                          ' found in the PhotoData-Photos.sqlite ZSHARE Table and supports iOS 14-15.' \
                          ' Parses iCloud Share Methods and Participant records only no asset data being parsed.' \
                          ' The iCloud Share methods being stored in these records include' \
                          ' Shred iCloud Links Cloud Master Moments-CMM and Shared iCloud Photo Library SPL.'
            report = ArtifactHtmlReport('Photos.sqlite-iCloud_Shared_Methods')
            report.start_artifact_report(report_folder, 'Ph30-iCloud Share Methods NAD-PhDaPsql', description)
            report.add_script()
            data_headers = ('zShare-Creation Date-0',
                            'zShare-Start Date-1',
                            'zShare-End Date-2',
                            'zShare-Expiry Date-3',
                            'zShare-UUID-4',
                            'zShare-Originating Scope ID-5',
                            'zShare-Status-6',
                            'zShare-Scope Type-7',
                            'zShare-Asset Count-8',
                            'zShare-Force Sync Attempted-9',
                            'zShare-Photos Count-10',
                            'zShare-Uploaded Photos Count-11',
                            'zShare-Videos Count-12',
                            'zShare-Uploaded Videos Count-13',
                            'zShare-Scope ID-14',
                            'zShare-Title-SPL-15',
                            'zShare-Share URL-16',
                            'zShare-Local Publish State-17',
                            'zShare-Public Permission-18',
                            'zSharePartic-Acceptance Status-19',
                            'zSharePartic-User ID-20',
                            'zSharePartic-zPK-21',
                            'zSharePartic-Email Address-22',
                            'zSharePartic-Phone Number-23',
                            'zSharePartic-Is Current User-24',
                            'zSharePartic-Role-25',
                            'zSharePartic-Premission-26',
                            'zShare-Should Notify On Upload Completion-27',
                            'zShare-Should Ignor Budgets-28',
                            'zShare-Trashed State-29',
                            'zShare-Cloud Delete State-30',
                            'zShare-zENT-31')
            report.write_artifact_data_table(data_headers, data_list, file_found)
            report.end_artifact_report()

            tsvname = 'Ph30-iCloud Share Methods NAD-PhDaPsql'
            tsv(report_folder, data_headers, data_list, tsvname)

            tlactivity = 'Ph30-iCloud Share Methods NAD-PhDaPsql'
            timeline(report_folder, tlactivity, data_list, data_headers)

        else:
            logfunc('No data available for PhotoData-Photos.sqlite ZSHARE iCloud Share Method icld links and SPL'
                    ' Records with No Asset Data')

        db.close()
        return

    elif version.parse(iosversion) >= version.parse("16"):
        file_found = str(files_found[0])
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()

        cursor.execute("""
        SELECT
        DateTime(zShare.ZCREATIONDATE + 978307200, 'UNIXEPOCH') AS 'zShare-Creation Date',
        DateTime(zShare.ZSTARTDATE + 978307200, 'UNIXEPOCH') AS 'zShare-Start Date',
        DateTime(zShare.ZENDDATE + 978307200, 'UNIXEPOCH') AS 'zShare-End Date',
        DateTime(zShare.ZEXPIRYDATE + 978307200, 'UNIXEPOCH') AS 'zShare-Expiry Date',
        zShare.ZUUID AS 'zShare-UUID',
        zShare.ZORIGINATINGSCOPEIDENTIFIER AS 'zShare-Originating Scope ID',
        CASE zSharePartic.Z54_SHARE
            WHEN 55 THEN '55-SPL-Entity-55'
            WHEN 56 THEN '56-CMM-iCloud-Link-Entity-56'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.Z54_SHARE || ''
        END AS 'zSharePartic-z54SHARE',
        CASE zShare.ZSTATUS
            WHEN 1 THEN '1-Active_Share-CMM_or_SPL-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSTATUS || ''
        END AS 'zShare-Status',
        CASE zShare.ZSCOPETYPE
            WHEN 2 THEN '2-iCloudLink-CMMoment-2'
            WHEN 4 THEN '4-iCld-Shared-Photo-Library-SPL-4'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSCOPETYPE || ''
        END AS 'zShare-Scope Type',
        zShare.ZCLOUDPHOTOCOUNT AS 'zShare-Cloud Photo Count',
        zShare.ZCOUNTOFASSETSADDEDBYCAMERASMARTSHARING AS 'zShare-CountOfAssets AddedByCamera Smart Sharing-HomeShare',
        zShare.ZCLOUDVIDEOCOUNT AS 'zShare-Cloud Video Count',
        zShare.ZASSETCOUNT AS 'zShare-Asset Count',
        zShare.ZFORCESYNCATTEMPTED AS 'zShare-Force Sync Attempted',  
        zShare.ZPHOTOSCOUNT AS 'zShare-Photos Count',
        zShare.ZUPLOADEDPHOTOSCOUNT AS 'zShare-Uploaded Photos Count',
        zShare.ZVIDEOSCOUNT AS 'zShare-Videos Count',
        zShare.ZUPLOADEDVIDEOSCOUNT AS 'zShare-Uploaded Videos Count',  
        zShare.ZSCOPEIDENTIFIER AS 'zShare-Scope ID',
        zShare.ZTITLE AS 'zShare-Title-SPL',
        zShare.ZSHAREURL AS 'zShare-Share URL',
        CASE zShare.ZLOCALPUBLISHSTATE
            WHEN 2 THEN '2-Published-2'
            ELSE 'Unknown-New-Value!: ' || zShare.ZLOCALPUBLISHSTATE || ''
        END AS 'zShare-Local Publish State',
        CASE zShare.ZPUBLICPERMISSION
            WHEN 1 THEN '1-Public_Premission_Denied-Private-1'
            WHEN 2 THEN '2-Public_Premission_Granted-Public-2'
            ELSE 'Unknown-New-Value!: ' || zShare.ZPUBLICPERMISSION || ''
        END AS 'zShare-Public Permission',
        CASE zShare.ZCLOUDLOCALSTATE
            WHEN 1 THEN '1-LocalandCloud-SPL-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZCLOUDLOCALSTATE || ''
        END AS 'zShare-Cloud Local State',
        CASE zShare.ZSCOPESYNCINGSTATE
            WHEN 1 THEN '1-ScopeAllowedToSync-SPL-StillTesting-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSCOPESYNCINGSTATE || ''
        END AS 'zShare-Scope Syncing State',
        CASE zShare.ZAUTOSHAREPOLICY
            WHEN 0 THEN '0-AutoShare-OFF_SPL_Test_NotAllAtSetup-0'
            ELSE 'Unknown-New-Value!: ' || zShare.ZAUTOSHAREPOLICY || ''
        END AS 'zShare-Auto Share Policy',  
        CASE zSharePartic.ZACCEPTANCESTATUS
            WHEN 1 THEN '1-Invite-Pending_or_Declined-1'
            WHEN 2 THEN '2-Invite-Accepted-2'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZACCEPTANCESTATUS || ''
        END AS 'zSharePartic-Acceptance Status',
        zSharePartic.ZUSERIDENTIFIER AS 'zSharePartic-User ID',
        zSharePartic.Z_PK AS 'zSharePartic-zPK',
        zSharePartic.ZEMAILADDRESS AS 'zSharePartic-Email Address',
        zSharePartic.ZPHONENUMBER AS 'zSharePartic-Phone Number',  
        zSharePartic.ZPARTICIPANTID AS 'zSharePartic-Participant ID',
        zSharePartic.ZUUID AS 'zSharePartic-UUID',  
        CASE zSharePartic.ZISCURRENTUSER
            WHEN 0 THEN '0-Participant-Not_CurrentUser-0'
            WHEN 1 THEN '1-Participant-Is_CurrentUser-1'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZISCURRENTUSER || ''
        END AS 'zSharePartic-Is Current User',
        CASE zSharePartic.ZROLE
            WHEN 1 THEN '1-Participant-is-Owner-Role-1'
            WHEN 2 THEN '2-Participant-is-Invitee-Role-2'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZROLE || ''
        END AS 'zSharePartic-Role',
        CASE zSharePartic.ZPERMISSION
            WHEN 3 THEN '3-Participant-has-Full-Premissions-3'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZPERMISSION || ''
        END AS 'zSharePartic-Premission',
        CASE zShare.ZPARTICIPANTCLOUDUPDATESTATE
            WHEN 2 THEN '2-ParticipantAllowedToUpdate_SPL_StillTesting-2'
            ELSE 'Unknown-New-Value!: ' || zShare.ZPARTICIPANTCLOUDUPDATESTATE || ''
        END AS 'zShare-Participant Cloud Update State', 
        CASE zSharePartic.ZEXITSTATE
            WHEN 0 THEN '0-NA_SPL_StillTesting'
            ELSE 'Unknown-New-Value!: ' || zSharePartic.ZEXITSTATE || ''
        END AS 'zSharePartic-Exit State',
        CASE zShare.ZPREVIEWSTATE
            WHEN 0 THEN '0-NotInPreviewState-StillTesting-SPL-0'
            ELSE 'Unknown-New-Value!: ' || zShare.ZPREVIEWSTATE || ''
        END AS 'zShare-Preview State',
        CASE zShare.ZSHOULDNOTIFYONUPLOADCOMPLETION
            WHEN 0 THEN '0-DoNotNotify-SPL-0'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSHOULDNOTIFYONUPLOADCOMPLETION || ''
        END AS 'zShare-Should Notify On Upload Completion',
        CASE zShare.ZSHOULDIGNOREBUDGETS
            WHEN 1 THEN '1-StillTesting-CMM-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZSHOULDIGNOREBUDGETS || ''
        END AS 'zShare-Should Ignor Budgets',
        CASE zShare.ZEXITSOURCE
            WHEN 0 THEN '0-NA_SPL_StillTesting'
            ELSE 'Unknown-New-Value!: ' || zShare.ZEXITSOURCE || ''
        END AS 'zShare-Exit Source',
        CASE zShare.ZEXITSTATE
            WHEN 0 THEN '0-NA_SPL_StillTesting'
            ELSE 'Unknown-New-Value!: ' || zShare.ZEXITSTATE || ''
        END AS 'zShare-Exit State',
        CASE zShare.ZEXITTYPE
            WHEN 0 THEN '0-NA_SPL_StillTesting'
            ELSE 'Unknown-New-Value!: ' || zShare.ZEXITTYPE || ''
        END AS 'zShare-Exit Type',
        CASE zShare.ZTRASHEDSTATE
            WHEN 0 THEN '0-Not_in_Trash-0'
            WHEN 1 THEN '1-In_Trash-1'
            ELSE 'Unknown-New-Value!: ' || zShare.ZTRASHEDSTATE || ''
        END AS 'zShare-Trashed State',
        CASE zShare.ZCLOUDDELETESTATE
            WHEN 0 THEN '0-Not Deleted-0'
            ELSE 'Unknown-New-Value!: ' || zShare.ZCLOUDDELETESTATE || ''
        END AS 'zShare-Cloud Delete State',
        DateTime(zShare.ZTRASHEDDATE + 978307200, 'UNIXEPOCH') AS 'zShare-Trashed Date',
        DateTime(zShare.ZLASTPARTICIPANTASSETTRASHNOTIFICATIONDATE + 978307200, 'UNIXEPOCH') AS
        'zShare-LastParticipant Asset Trash Notification Date',
        DateTime(zShare.ZLASTPARTICIPANTASSETTRASHNOTIFICATIONVIEWEDDATE + 978307200, 'UNIXEPOCH') AS
        'zShare-Last Participant Asset Trash Notification View Date',
        CASE zShare.Z_ENT
            WHEN 55 THEN '55-SPL-Entity-55'
            WHEN 56 THEN '56-CMM-iCloud-Link-Entity-56'
            ELSE 'Unknown-New-Value!: ' || zShare.Z_ENT || ''
        END AS 'zShare-zENT'
        FROM ZSHARE zShare
            LEFT JOIN ZSHAREPARTICIPANT zSharePartic ON zSharePartic.ZSHARE = zShare.Z_PK
        ORDER BY zShare.ZCREATIONDATE
        """)

        all_rows = cursor.fetchall()
        usageentries = len(all_rows)
        data_list = []
        counter = 0
        if usageentries > 0:
            for row in all_rows:
                data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
                                  row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18],
                                  row[19], row[20], row[21], row[22], row[23], row[24], row[25], row[26], row[27],
                                  row[28], row[29], row[30], row[31], row[32], row[33], row[34], row[35], row[36],
                                  row[37], row[38], row[39], row[40], row[41], row[42], row[43], row[44], row[45],
                                  row[46], row[47], row[48], row[49]))

                counter += 1

            description = 'Parses records for different methods which media files have been shared via iCloud Share' \
                          ' found in the PhotoData-Photos.sqlite ZSHARE Table and supports iOS 16-17.' \
                          ' Parses iCloud Share Methods and Participant records only no asset data being parsed.' \
                          ' The iCloud Share methods being stored in these records include' \
                          ' Shred iCloud Links Cloud Master Moments-CMM and Shared iCloud Photo Library SPL.'
            report = ArtifactHtmlReport('Photos.sqlite-iCloud_Shared_Methods')
            report.start_artifact_report(report_folder, 'Ph30-iCloud Share Methods NAD-PhDaPsql', description)
            report.add_script()
            data_headers = ('zShare-Creation Date-0',
                            'zShare-Start Date-1',
                            'zShare-End Date-2',
                            'zShare-Expiry Date-3',
                            'zShare-UUID-4',
                            'zShare-Originating Scope ID-5',
                            'zSharePartic-z54SHARE-6',
                            'zShare-Status-7',
                            'zShare-Scope Type-8',
                            'zShare-Cloud Photo Count-9',
                            'zShare-CountOfAssets AddedByCamera Smart Sharing-HomeShare-10',
                            'zShare-Cloud Video Count-11',
                            'zShare-Asset Count-12',
                            'zShare-Force Sync Attempted-13',
                            'zShare-Photos Count-14',
                            'zShare-Uploaded Photos Count-15',
                            'zShare-Videos Count-16',
                            'zShare-Uploaded Videos Count-17',
                            'zShare-Scope ID-18',
                            'zShare-Title-SPL-19',
                            'zShare-Share URL-20',
                            'zShare-Local Publish State-21',
                            'zShare-Public Permission-22',
                            'zShare-Cloud Local State-23',
                            'zShare-Scope Syncing State-24',
                            'zShare-Auto Share Policy-25',
                            'zSharePartic-Acceptance Status-26',
                            'zSharePartic-User ID-27',
                            'zSharePartic-zPK-28',
                            'zSharePartic-Email Address-29',
                            'zSharePartic-Phone Number-30',
                            'zSharePartic-Participant ID-31',
                            'zSharePartic-UUID-32',
                            'zSharePartic-Is Current User-33',
                            'zSharePartic-Role-34',
                            'zSharePartic-Premission-35',
                            'zShare-Participant Cloud Update State-36',
                            'zSharePartic-Exit State-37',
                            'zShare-Preview State-38',
                            'zShare-Should Notify On Upload Completion-39',
                            'zShare-Should Ignor Budgets-40',
                            'zShare-Exit Source-41',
                            'zShare-Exit State-42',
                            'zShare-Exit Type-43',
                            'zShare-Trashed State-44',
                            'zShare-Cloud Delete State-45',
                            'zShare-Trashed Date-46',
                            'zShare-LastParticipant Asset Trash Notification Date-47',
                            'zShare-Last Participant Asset Trash Notification View Date-48',
                            'zShare-zENT-49')
            report.write_artifact_data_table(data_headers, data_list, file_found)
            report.end_artifact_report()

            tsvname = 'Ph30-iCloud Share Methods NAD-PhDaPsql'
            tsv(report_folder, data_headers, data_list, tsvname)

            tlactivity = 'Ph30-iCloud Share Methods NAD-PhDaPsql'
            timeline(report_folder, tlactivity, data_list, data_headers)

        else:
            logfunc('No data available for PhotoData-Photos.sqlite ZSHARE iCloud Share Method icld links and SPL'
                    ' Records with No Asset Data')

        db.close()
        return


__artifacts_v2__ = {
    'Ph30-iCloud Shared Methods with NAD-PhDaPsql': {
        'name': 'PhDaPL Photos.sqlite 30 iCld Share Methods with No Asset Data',
        'description': 'Parses records for different methods which media files have been shared via iCloud Share'
                       ' found in the PhotoData-Photos.sqlite ZSHARE Table and supports iOS 14-17.'
                       ' Parses iCloud Share Methods and Participant records only no asset data being parsed.'
                       ' The iCloud Share methods being stored in these records include'
                       ' Shred iCloud Links Cloud Master Moments-CMM and Shared iCloud Photo Library SPL.',
        'author': 'Scott Koenig https://theforensicscooter.com/',
        'version': '1.2',
        'date': '2024-04-12',
        'requirements': 'Acquisition that contains PhotoData-Photos.sqlite',
        'category': 'Photos.sqlite-iCloud_Shared_Methods',
        'notes': '',
        'paths': '*/mobile/Media/PhotoData/Photos.sqlite*',
        'function': 'get_ph30icldsharemethphdapsql'
    }
}
