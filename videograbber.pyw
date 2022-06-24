"""
    file: videograbber.py
    author: ed c

    obs websocket doc: https://github.com/obsproject/obs-websocket/blob/4.x-current/docs/generated/protocol.md
"""

# TODO: Configuration file (use videograbber.json)
# TODO: OBS Event: 'SourceDestroyed', Raw data: {'sourceKind': 'scene', 'sourceName': 'Scene', 'sourceType': 'scene', 'update-type': 'SourceDestroyed'}: close app
# TODO: use OS instead of OBS to get disk space (so no exception if obs is closed and disk space wants to be updated)
# TODO: capture OS events (i.e., close app, etc.)
# TODO: consider closing preview and using projector instead
# TODO: catch OBS events
# TODO: installer (installation instructions)
# TODO: (OBS) create sources, lock configuration files
# TODO: check, set Sources, Profile, Scene (create standards for these)
# TODO: set filename format (SetFilenameFormatting)
# TODO: QSG (have this app set all parameters so no manual settings are required)
# TODO: warn on version mismatch for OBS, websockets and simpleobsws
# TODO: catch errors
# TODO: USB disconnect
# TODO: OBS status, Popen.wait(), Popen.poll() (https://docs.python.org/3/library/subprocess.html)
# XXXX: Consider: start OBS (shell:startup) so it can't be changed by user/patron (but if it reboots...): start/stop a projector
# XXXX: automatic file naming
# DONE: show elapsed recording time
# DONE: show OBS recording time on stop recording (use GetRecordingStatus before stopping)
# DONE: show filename of current recording
# DONE: show OBS info on F1?
# DONE: Show available disk space
# DONE: warn on low disk space
# DONE: disable buttons when not valid

import asyncio
import simpleobsws
from tkinter import *
import psutil
import subprocess
from datetime import timedelta
from os.path import basename
from time import sleep

debug = True

vr_version = '0.6'

parms = {
    # main window
    'icon' : 'VideoGrabberIcon.ico',
    'vr_title' : 'Riverton FamilySearch Library Video Grabber',
    'vr_geometry' : '500x220+72+32',
    'font_family' : 'Consolas',
    'font_bold' : 'Consolas Bold',
    'font_italic' : 'Consolas Italic',

    # OBS
    'obs_processname' : 'obs64.exe',
    'obs_command' : r'C:\Program Files\obs-studio\bin\64bit\obs64.exe',
    'obs_directory' : r'C:\Program Files\obs-studio\bin\64bit',
    'obs_startup_parms' : '--disable-updater', # was r'--always-on-top'

    # OBS interface
    'obs_pswd' : 'family',
    'obs_host' : '127.0.0.1',
    'obs_port' : 4444,

}

obs_version = ''
obs_status = ''
ws_version = ''

expected_obs_version = '27.2.4'
expected_ws_version = '4.9.1'
expected_simpleobsws_version = '1.1'


obs_pswd = 'family'

bg_color = 'SystemButtonFace'
bg_alpha = 0.95

#parms['font_family'] = 'Consolas'

obs_command = r'C:\Program Files\obs-studio\bin\64bit\obs64.exe'
obs_directory = r'C:\Program Files\obs-studio\bin\64bit'
obs_startup_parms = r'--minimize-to-tray'

btn_font = parms['font_family'] + ' Bold'
btn_font_size = 16
btn_height = 3
btn_width = 8

st_font = parms['font_family'] + ' Bold'
st_font_size = 16

recording_filename_font = parms['font_family']
recording_filename_fontsize = 11

recording_in_progress = False
elapsed_time = 0
elapsed_time_font = parms['font_family']
elapsed_time_fontsize = 11
elapsed_time_after = None

free_disk = 0.0
free_disk_min = 5000.0
fd_font = parms['font_family']
fd_font_size = 12
fd_delay = 60000  # 60000 to update available disk space once a minute

app_status_font = parms['font_family'] + ' Bold'
app_status_font_size = 12

info_line_font = parms['font_family'] + ' Italic'
info_line_font_size = 8

async def get_obs_info( ):
    global parms, obs_version, ws_version, obs_status
    ##await ws.connect()
    info = await ws.call( 'GetVersion' )
    if debug: print( f'GetVersion: {info}')
    obs_version = info[ 'obs-studio-version' ]
    ws_version = info[ 'obs-websocket-version' ]
    obs_status = info[ 'status' ]
    await asyncio.sleep( 1 )
    ##await ws.disconnect()
    if debug: print( f'vr: {vr_version}, obs: {obs_version}, ws: {ws_version}, status: {obs_status}')

async def get_obs_disk_space( ):
    global free_disk
    ##await ws.connect( )
    stats = await ws.call( 'GetStats' )
    if debug: print( f'GetStats: {stats}')
    free_disk = float( stats[ 'stats' ][ 'free-disk-space' ] )
    await asyncio.sleep( 1 )
    ##await ws.disconnect( )
       
def show_disk_space( ):
    global free_disk
    loopy.run_until_complete( get_obs_disk_space() )
    if free_disk < free_disk_min:
        ds.config( bg = 'Red' )
    else:
        ds.config( bg = bg_color )
    disk_space_text.set( f'Available disk space: {free_disk/1024:.1f}G ' )
    vr.after( fd_delay, show_disk_space )

async def __start_recording( ):
    ##await ws.connect()
    rc = await ws.call( 'StartRecording' )   
    if debug: print( f'start_recording rc: {rc}')
    await asyncio.sleep( 1 )
    info = await( ws.call( 'GetRecordingStatus' ) )
    recording_filename.set( basename( info[ 'recordingFilename' ] ) )
    ##await ws.disconnect( )

def start_recording( ):
    global recording_in_progress, elapsed_time
    btn_start[ 'state' ] = DISABLED
    show_app_status( 'Do NOT close OBS: the recording will fail', 'DarkRed' )
    recording_in_progress = True
    loopy.run_until_complete( __start_recording( ) )
    show_recording_status( 'Recording', 'Red' )
    elapsed_time = 0
    show_elapsed_time()
    btn_stop[ 'state' ] = NORMAL

async def __stop_recording( ):
    ##await ws.connect()
    # TODO: use GetRecordingStatus to get the length of the recording
    info = await( ws.call( 'GetRecordingStatus' ) )
    await asyncio.sleep( 1 )
    if debug: print( f'GetRecordingStatus.recordTimecode {info[ "recordTimecode" ]}')
    recording_time.set( info[ 'recordTimecode' ] )
    rc = await ws.call( 'StopRecording' )    
    if debug: print( f'stop_recording rc: {rc}')   
    ##await ws.disconnect( )

def stop_recording( ):
    global recording_in_progress, elapsed_time_after
    recording_in_progress = False
    vr.after_cancel( elapsed_time_after ) # stop the elapsed time counter and display
    btn_stop[ 'state' ] = DISABLED
    loopy.run_until_complete( __stop_recording( ) )    
    show_recording_status( 'Stopped', 'Black' )
    show_app_status( f'File "{recording_filename.get()}" saved to the desktop', 'DarkGreen' )
    btn_start[ 'state' ] = NORMAL


def show_recording_status( txt, color ): # Show status message next to buttons
    recording_state_label.config( fg = color )
    recording_state.set( txt )

def show_app_status( txt, color='Grey' ):
    app_status.config( fg = color )
    app_status_text.set( txt )

def show_elapsed_time():
    global recording_in_progress, elapsed_time, elapsed_time_after
    if debug: print( f'show_elapsed_time: {elapsed_time}')
    if recording_in_progress:
        recording_time.set( str( timedelta( seconds=elapsed_time ) ) )
        elapsed_time += 1
        elapsed_time_after = vr.after( 1000, show_elapsed_time )
    #else:
        #recording_time.set( '' )


def is_process_running( processName ): # https://thispointer.com/python-check-if-a-process-is-running-by-name-and-find-its-process-id-pid/
    ''' Check if there is any running process that contains the given name processName. '''
    for proc in psutil.process_iter(): #Iterate over the all the running processes
        try:
            if processName.lower() in proc.name().lower(): # Check if process name contains the given name string
                if debug: print( f'{processName} is running')
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            if debug: print( f'{processName} NOT running')
            return False
        except (psutil.ZombieProcess):
            # TODO: need to kill it
            return False

def start_obs( ):
    global parms
    show_app_status('Starting OBS', 'Black')
    vr.update()
    try:
        rc = subprocess.Popen([parms['obs_command'], parms['obs_startup_parms']], cwd = parms['obs_directory'])
        show_app_status('Waiting for OBS to be ready', 'Black')
        vr.update()
        sleep(4) # 3 works, but barely; using 4 in case of a Blue Moon
        show_app_status('')
        vr.update()
        if debug: print( f'Popen succeeded, returning {rc}')
        return True
    except:
        btn_start[ 'state' ] = DISABLED
        btn_stop[ 'state' ] = DISABLED
        show_app_status( 'ERROR: OBS could not be started', 'Red' )
        if debug: print( 'ERROR: OBS could not be started' ) 
        return False

def check_obs( ):
    global parms
    # if OBS isn't running, start it
    if not is_process_running( parms['obs_processname'] ):
        if( start_obs() ):
            show_app_status( 'OBS is running' )
            return True
        else:
            show_app_status( 'ERROR: OBS could not be started', 'Red')
            btn_start[ 'state' ] = DISABLED
            btn_stop[ 'state' ] = DISABLED
            return False
    else:
        return True
        

async def start_obs_projector( ):
    ##await ws.connect()
    rc = await ws.call( 'OpenProjector' )   
    if debug: print( f'OpenProjector rc: {rc}')
    ##await ws.disconnect( )

async def __configure_obs( ):
    ##await ws.connect()
    #rc = await ws.call( 'SetFilenameFormatting' ) 
    #if debug: print( f'SetFilenameFormatting: {rc}') 
    # TODO: GetSourcesList, CreateSource, SetVolume, SetSourceSettings, SetCurrentProfile, ListProfiles, GetRecordingStatus, SetRecordingFolder, SetCurrentScene, CreateScene,  
    await asyncio.sleep( 1 )
    ##await ws.disconnect( )

def configure_obs( ):
    loopy.run_until_complete( __configure_obs( ) )

async def on_obs_event( data ):
    print( f'OBS Event: \'{data["update-type"]}\', Raw data: {data}')
    if data[ 'update-type' ] == 'SourceDestroyed':
        print( 'OBS closed, forcing exit' )
        show_app_status( 'OBS closed, forcing exit' )
        await asyncio.sleep( 3 )
        vr.destroy()
        exit( )

def log_callback( ): 
    pass  

#------
if __name__ == '__main__':
    vr = Tk()
    vr.attributes( '-alpha', bg_alpha ) # set transparency
    vr.attributes( '-topmost', 1 ) # force it to stay on top (so user doesn't lose it)
    vr.geometry(parms['vr_geometry'])
    vr.resizable( False, False )
    vr.title(parms['vr_title'])
    vr.iconbitmap( 'VideoGrabberIcon.ico' )  

    # frame for start button
    fr1 = Frame( master=vr, padx = 8, pady = 8 )
    fr1.grid( row=0, column=0, rowspan=3, padx = 4, pady = 4, sticky='wn' )

    # create 'start' button
    btn_start = Button( fr1, text = 'Record',
        height=btn_height, width=btn_width,
        command = start_recording,
        font = ( btn_font, btn_font_size ),
        fg='Red'
        )
    btn_start.grid( row=0, column=0 )

     # frame for stop
    fr2 = Frame( master=vr, padx = 8, pady = 8 )
    fr2.grid( row=0, column=1, rowspan=3, padx = 4, pady = 4, sticky='wn' )
   
    # create 'stop' button
    btn_stop = Button( fr2, text = 'Stop',
        height=btn_height, width=btn_width,
        command = stop_recording,
        state = DISABLED,
        font = ( btn_font, btn_font_size )
        )
    btn_stop.grid( row=0, column=0 )

    # frame/label for recording state, filename, time
    recording_state_frame = Frame( master=vr, padx=8, pady=8 )
    recording_state_frame.grid( row=0, column=2, padx=4, pady=4, sticky='wn')
    recording_state = StringVar()
    recording_state_label = Label( recording_state_frame, textvariable=recording_state, font=( st_font, st_font_size ), anchor='w' )
    recording_state_label.grid( sticky='w' )

    # frame/label for output filename
    #recording_filename_frame = Frame( master=vr, padx=8, pady=8 )
    #recording_filename_frame.grid( row=1, column=2, padx=4, pady=4, sticky='w')
    recording_filename = StringVar()
    recording_filename_label = Label( recording_state_frame, textvariable=recording_filename, font=( recording_filename_font, recording_filename_fontsize ), anchor='w' )
    recording_filename_label.grid( sticky='w')
    
    # frame/label for recording time
    #recording_time_frame = Frame( master=vr, padx=8, pady=8 )
    #recording_time_frame.grid( row=2, column=2, padx=4, pady=4, sticky='ws' )
    recording_time = StringVar()
    recording_time_label = Label( recording_state_frame, textvariable=recording_time, font=( elapsed_time_font, elapsed_time_fontsize ), anchor='w' )
    recording_time_label.grid( sticky='w' )

    # frame/label for disk space
    fr3 = Frame( master=vr, padx = 8, pady = 8 )
    fr3.grid( row = 3, column=0, columnspan=3, sticky='w' )
    disk_space_text = StringVar()
    ds = Label( fr3, textvariable=disk_space_text, font=( fd_font, fd_font_size ), anchor='w' )
    ds.grid( sticky='w')
    ds.config( fg='Black' )
    #if debug: print( f'default background color: {ds.cget( "background" )}')

    # frame/label for app status
    app_status_frame = Frame( master=vr, padx = 8, pady = 8 )
    app_status_frame.grid( row = 4, column=0, columnspan=3, sticky='w' )
    app_status_text = StringVar()
    app_status = Label( fr3, textvariable=app_status_text, font=( app_status_font, app_status_font_size ), anchor='w' )
    app_status.grid( sticky='w' )

    info_line_frame = Frame( master=vr, padx = 8, pady = 8 )
    info_line_frame.grid( row = 5, column=0, columnspan=3, sticky='w' )
    info_line_text = StringVar()
    info_line = Label( info_line_frame, textvariable=info_line_text, font=( info_line_font, info_line_font_size ) )
    info_line.grid( sticky='' )

    vr.update()

    loopy = asyncio.get_event_loop()

    if( check_obs( ) ): # if OBS start ok, then we can proceed
        # set up an interface to OBS Studio
        ws = simpleobsws.obsws(host=parms['obs_host'], port=parms['obs_port'], password=parms['obs_pswd'], loop=loopy)
        loopy.run_until_complete( ws.connect() )
        ws.register( on_obs_event )

        loopy.run_until_complete( get_obs_info( ) )
        info_line.config( fg='Grey')
        info_line_text.set( f'vr: {vr_version}, obs: {obs_version}, ws: {ws_version}, status: {obs_status}' )

        vr.update()

        show_disk_space() # schedules itself to re-run every fd_delay milliseconds (default one minute)

        #loopy.run_until_complete( start_obs_projector( ) )
        
        if debug: print( 'all set; entering the tk forever loop' )
    else:
        show_app_status( 'ERROR: OBS could not be started. Restart me.', 'Red')
        vr.update()
        sleep( 8 )
        vr.destroy()
        exit( 17 )

    vr.mainloop()
