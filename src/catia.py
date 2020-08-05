#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# JACK Patchbay
# Copyright (C) 2010-2020 Filipe Coelho <falktx@falktx.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the COPYING file

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom Stuff)

import ui_catia
from shared_canvasjack import *
from shared_settings import *

from PyQt5.QtWidgets import QInputDialog, QLineEdit

# ------------------------------------------------------------------------------------------------------------
# Try Import OpenGL

try:
    from PyQt5.QtOpenGL import QGLWidget
    hasGL = True
except:
    hasGL = False

# ------------------------------------------------------------------------------------------------------------
# Static Variables

iGroupId   = 0
iGroupName = 1

iPortId        = 0
iPortName      = 1
iPortNameR     = 2
iPortGroupId   = 3
iPortGroupName = 4

iConnId       = 0
iConnOutGroup = 1
iConnOutPort  = 2
iConnInGroup  = 3
iConnInPort   = 4

URI_MAIN_CLIENT_NAME = "https://kx.studio/ns/carla/main-client-name"
URI_POSITION         = "https://kx.studio/ns/carla/position"
URI_PLUGIN_ICON      = "https://kx.studio/ns/carla/plugin-icon"
URI_PLUGIN_ID        = "https://kx.studio/ns/carla/plugin-id"

URI_TYPE_INTEGER = "http://www.w3.org/2001/XMLSchema#integer"
URI_TYPE_STRING  = "text/plain"

# ------------------------------------------------------------------------------------------------------------
# Catia Main Window

class CatiaMainW(AbstractCanvasJackClass):
    def __init__(self, parent=None):
        AbstractCanvasJackClass.__init__(self, "Catia", ui_catia.Ui_CatiaMainW, parent)

        self.fGroupList      = []
        self.fGroupSplitList = []
        self.fPortList       = []
        self.fConnectionList = []

        self.fLastGroupId = 1
        self.fLastPortId  = 1
        self.fLastConnectionId = 1

        self.loadSettings(True)

        # -------------------------------------------------------------
        # Set-up GUI

        self.ui.act_canvas_arrange.setIcon(getIcon("view-sort-ascending"))
        self.ui.act_canvas_refresh.setIcon(getIcon("view-refresh"))
        self.ui.act_canvas_zoom_fit.setIcon(getIcon("zoom-fit-best"))
        self.ui.act_canvas_zoom_in.setIcon(getIcon("zoom-in"))
        self.ui.act_canvas_zoom_out.setIcon(getIcon("zoom-out"))
        self.ui.act_canvas_zoom_100.setIcon(getIcon("zoom-original"))
        self.ui.b_canvas_zoom_fit.setIcon(getIcon("zoom-fit-best"))
        self.ui.b_canvas_zoom_in.setIcon(getIcon("zoom-in"))
        self.ui.b_canvas_zoom_out.setIcon(getIcon("zoom-out"))
        self.ui.b_canvas_zoom_100.setIcon(getIcon("zoom-original"))

        self.ui.act_jack_clear_xruns.setIcon(getIcon("edit-clear"))

        self.ui.act_transport_play.setIcon(getIcon("media-playback-start"))
        self.ui.act_transport_stop.setIcon(getIcon("media-playback-stop"))
        self.ui.act_transport_backwards.setIcon(getIcon("media-seek-backward"))
        self.ui.act_transport_forwards.setIcon(getIcon("media-seek-forward"))
        self.ui.b_transport_play.setIcon(getIcon("media-playback-start"))
        self.ui.b_transport_stop.setIcon(getIcon("media-playback-stop"))
        self.ui.b_transport_backwards.setIcon(getIcon("media-seek-backward"))
        self.ui.b_transport_forwards.setIcon(getIcon("media-seek-forward"))

        self.ui.act_quit.setIcon(getIcon("application-exit"))
        self.ui.act_configure.setIcon(getIcon("configure"))

        self.ui.cb_buffer_size.clear()
        self.ui.cb_sample_rate.clear()

        for bufferSize in BUFFER_SIZE_LIST:
            self.ui.cb_buffer_size.addItem(str(bufferSize))

        # -------------------------------------------------------------
        # Set-up Canvas

        self.scene = patchcanvas.PatchScene(self, self.ui.graphicsView)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing, bool(self.fSavedSettings["Canvas/Antialiasing"] == patchcanvas.ANTIALIASING_FULL))
        if self.fSavedSettings["Canvas/UseOpenGL"] and hasGL:
            self.ui.graphicsView.setViewport(QGLWidget(self.ui.graphicsView))
            self.ui.graphicsView.setRenderHint(QPainter.HighQualityAntialiasing, self.fSavedSettings["Canvas/HighQualityAntialiasing"])

        pOptions = patchcanvas.options_t()
        pOptions.theme_name        = self.fSavedSettings["Canvas/Theme"]
        pOptions.auto_hide_groups  = self.fSavedSettings["Canvas/AutoHideGroups"]
        pOptions.use_bezier_lines  = self.fSavedSettings["Canvas/UseBezierLines"]
        pOptions.antialiasing      = self.fSavedSettings["Canvas/Antialiasing"]
        pOptions.eyecandy          = self.fSavedSettings["Canvas/EyeCandy"]
        pOptions.auto_select_items = False # TODO
        pOptions.inline_displays   = False

        pFeatures = patchcanvas.features_t()
        pFeatures.group_info   = False
        pFeatures.group_rename = False
        pFeatures.port_info    = True
        pFeatures.port_rename  = bool(self.fSavedSettings["Main/JackPortAlias"] > 0)
        pFeatures.handle_group_pos = True

        patchcanvas.setOptions(pOptions)
        patchcanvas.setFeatures(pFeatures)
        patchcanvas.init("Catia", self.scene, self.canvasCallback, DEBUG)

        # -------------------------------------------------------------
        # Try to connect to jack

        self.jackStarted()

        # -------------------------------------------------------------
        # Set-up Timers

        self.fTimer120 = self.startTimer(self.fSavedSettings["Main/RefreshInterval"])
        self.fTimer600 = self.startTimer(self.fSavedSettings["Main/RefreshInterval"] * 5)

        # -------------------------------------------------------------
        # Set-up Connections

        self.ui.act_canvas_arrange.setEnabled(False) # TODO, later
        self.ui.act_canvas_arrange.triggered.connect(self.slot_canvasArrange)
        self.ui.act_canvas_refresh.triggered.connect(self.slot_canvasRefresh)
        self.ui.act_canvas_zoom_fit.triggered.connect(self.slot_canvasZoomFit)
        self.ui.act_canvas_zoom_in.triggered.connect(self.slot_canvasZoomIn)
        self.ui.act_canvas_zoom_out.triggered.connect(self.slot_canvasZoomOut)
        self.ui.act_canvas_zoom_100.triggered.connect(self.slot_canvasZoomReset)
        self.ui.act_canvas_save_image.triggered.connect(self.slot_canvasSaveImage)
        self.ui.b_canvas_zoom_fit.clicked.connect(self.slot_canvasZoomFit)
        self.ui.b_canvas_zoom_in.clicked.connect(self.slot_canvasZoomIn)
        self.ui.b_canvas_zoom_out.clicked.connect(self.slot_canvasZoomOut)
        self.ui.b_canvas_zoom_100.clicked.connect(self.slot_canvasZoomReset)

        self.ui.act_jack_clear_xruns.triggered.connect(self.slot_JackClearXruns)
        self.ui.cb_buffer_size.currentIndexChanged[str].connect(self.slot_jackBufferSize_ComboBox)
        self.ui.b_xruns.clicked.connect(self.slot_JackClearXruns)

        self.ui.act_transport_play.triggered.connect(self.slot_transportPlayPause)
        self.ui.act_transport_stop.triggered.connect(self.slot_transportStop)
        self.ui.act_transport_backwards.triggered.connect(self.slot_transportBackwards)
        self.ui.act_transport_forwards.triggered.connect(self.slot_transportForwards)
        self.ui.b_transport_play.clicked.connect(self.slot_transportPlayPause)
        self.ui.b_transport_stop.clicked.connect(self.slot_transportStop)
        self.ui.b_transport_backwards.clicked.connect(self.slot_transportBackwards)
        self.ui.b_transport_forwards.clicked.connect(self.slot_transportForwards)
        self.ui.label_time.customContextMenuRequested.connect(self.slot_transportViewMenu)

        self.ui.act_configure.triggered.connect(self.slot_configureCatia)

        self.ui.act_help_about.triggered.connect(self.slot_aboutCatia)
        self.ui.act_help_about_qt.triggered.connect(app.aboutQt)

        self.XRunCallback.connect(self.slot_XRunCallback)
        self.BufferSizeCallback.connect(self.slot_BufferSizeCallback)
        self.SampleRateCallback.connect(self.slot_SampleRateCallback)
        self.ClientRenameCallback.connect(self.slot_ClientRenameCallback)
        self.PortRegistrationCallback.connect(self.slot_PortRegistrationCallback)
        self.PortConnectCallback.connect(self.slot_PortConnectCallback)
        self.PortRenameCallback.connect(self.slot_PortRenameCallback)
        self.PropertyChangeCallback.connect(self.slot_PropertyChangeCallback)
        self.ShutdownCallback.connect(self.slot_ShutdownCallback)

        # -------------------------------------------------------------

    def canvasCallback(self, action, value1, value2, valueStr):
        if action == patchcanvas.ACTION_GROUP_INFO:
            pass

        elif action == patchcanvas.ACTION_GROUP_RENAME:
            pass

        elif action == patchcanvas.ACTION_GROUP_SPLIT:
            groupId = value1
            patchcanvas.splitGroup(groupId)

        elif action == patchcanvas.ACTION_GROUP_JOIN:
            groupId = value1
            patchcanvas.joinGroup(groupId)

        elif action == patchcanvas.ACTION_GROUP_POSITION:
            groupId = value1
            x1, y1, x2, y2 = tuple(int(i) for i in valueStr.split(":"))
            groupName = self.canvas_getGroupName(groupId)
            if not groupName:
                return
            uuidstr = jacklib.get_uuid_for_client_name(gJack.client, groupName)
            if uuidstr is None:
                return
            value = "%i:%i:%i:%i" % (x1, y1, x2, y2)
            jacklib.set_property(gJack.client, jacklib.uuid_parse(uuidstr), URI_POSITION, value, "text/plain")

        elif action == patchcanvas.ACTION_PORT_INFO:
            groupId = value1
            portId = value2

            for port in self.fPortList:
                if port[iPortId] == portId and port[iPortGroupId] == groupId:
                    portNameR = port[iPortNameR]
                    portNameG = port[iPortGroupName]
                    break
            else:
                return

            portPtr   = jacklib.port_by_name(gJack.client, portNameR)
            portFlags = jacklib.port_flags(portPtr)
            groupName = portNameR.split(":", 1)[0]
            portShortName = jacklib.port_short_name(portPtr)

            aliases = jacklib.port_get_aliases(portPtr)
            if aliases[0] == 1:
                alias1text = aliases[1]
                alias2text = "(none)"
            elif aliases[0] == 2:
                alias1text = aliases[1]
                alias2text = aliases[2]
            else:
                alias1text = "(none)"
                alias2text = "(none)"

            flags = []
            if portFlags & jacklib.JackPortIsInput:
                flags.append(self.tr("Input"))
            if portFlags & jacklib.JackPortIsOutput:
                flags.append(self.tr("Output"))
            if portFlags & jacklib.JackPortIsPhysical:
                flags.append(self.tr("Physical"))
            if portFlags & jacklib.JackPortCanMonitor:
                flags.append(self.tr("Can Monitor"))
            if portFlags & jacklib.JackPortIsTerminal:
                flags.append(self.tr("Terminal"))

            flagsText = " | ".join(flags)

            portTypeStr = jacklib.port_type(portPtr)
            if portTypeStr == jacklib.JACK_DEFAULT_AUDIO_TYPE:
                typeText = self.tr("JACK Audio")
            elif portTypeStr == jacklib.JACK_DEFAULT_MIDI_TYPE:
                typeText = self.tr("JACK MIDI")
            else:
                typeText = self.tr("Unknown")

            portLatency      = jacklib.port_get_latency(portPtr)
            portTotalLatency = jacklib.port_get_total_latency(gJack.client, portPtr)
            latencyText      = self.tr("%.1f ms (%i frames)" % (portLatency * 1000 / int(self.fSampleRate), portLatency))
            latencyTotalText = self.tr("%.1f ms (%i frames)" % (portTotalLatency * 1000 / int(self.fSampleRate), portTotalLatency))

            info = self.tr(""
                           "<table>"
                           "<tr><td align='right'><b>Group Name:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td align='right'><b>Port Name:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td align='right'><b>Full Port Name:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td align='right'><b>Port Alias #1:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td align='right'><b>Port Alias #2:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td colspan='2'>&nbsp;</td></tr>"
                           "<tr><td align='right'><b>Port Flags:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td align='right'><b>Port Type:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td colspan='2'>&nbsp;</td></tr>"
                           "<tr><td align='right'><b>Port Latency:</b></td><td>&nbsp;%s</td></tr>"
                           "<tr><td align='right'><b>Total Port Latency:</b></td><td>&nbsp;%s</td></tr>"
                           "</table>" % (groupName, portShortName, portNameR, alias1text, alias2text, flagsText, typeText, latencyText, latencyTotalText))

            QMessageBox.information(self, self.tr("Port Information"), info)

        elif action == patchcanvas.ACTION_PORT_RENAME:
            groupId = value1
            portId = value2

            oldName = self.canvas_getGroupName(groupId)

            if not oldName:
                return

            newNameTry = QInputDialog.getText(self,
                                              self.tr("Rename port"),
                                              self.tr("New port name:"), QLineEdit.Normal, oldName)

            if not (newNameTry[1] and newNameTry[0] and oldName != newNameTry[0]):
                return

            newName = newNameTry[0]

            for port in self.fPortList:
                if port[iPortId] == portId:
                    portNameR = port[iPortNameR]
                    portName = "%s:%s" % (port[iPortGroupName], newName)
                    break
            else:
                return

            portPtr = jacklib.port_by_name(gJack.client, portNameR)
            aliases = jacklib.port_get_aliases(portPtr)

            if aliases[0] == 2:
                # JACK only allows 2 aliases, remove 2nd
                jacklib.port_unset_alias(portPtr, aliases[2])

                # If we're going for 1st alias, unset it too
                if self.fSavedSettings["Main/JackPortAlias"] == 1:
                    jacklib.port_unset_alias(portPtr, aliases[1])

            elif aliases[0] == 1 and self.fSavedSettings["Main/JackPortAlias"] == 1:
                jacklib.port_unset_alias(portPtr, aliases[1])

            if aliases[0] == 0 and self.fSavedSettings["Main/JackPortAlias"] == 2:
                # If 2nd alias is enabled and port had no previous aliases, set the 1st alias now
                jacklib.port_set_alias(portPtr, portName)

            if jacklib.port_set_alias(portPtr, portName) == 0:
                patchcanvas.renamePort(groupId, portId, newName)

        elif action == patchcanvas.ACTION_PORTS_CONNECT:
            gOut, pOut, gIn, pIn = tuple(int(i) for i in valueStr.split(":"))

            portRealNameOut = ""
            portRealNameIn = ""

            for port in self.fPortList:
                if port[iPortGroupId] == gOut and port[iPortId] == pOut:
                    portRealNameOut = port[iPortNameR]
                elif port[iPortGroupId] == gIn and port[iPortId] == pIn:
                    portRealNameIn = port[iPortNameR]

            if portRealNameOut and portRealNameIn:
                jacklib.connect(gJack.client, portRealNameOut, portRealNameIn)

        elif action == patchcanvas.ACTION_PORTS_DISCONNECT:
            connectionId = value1

            for connection in self.fConnectionList:
                if connection[iConnId] == connectionId:
                    gOut, pOut, gIn, pIn = connection[1:]
                    break
            else:
                return

            portRealNameOut = ""
            portRealNameIn = ""

            for port in self.fPortList:
                if port[iPortGroupId] == gOut and port[iPortId] == pOut:
                    portRealNameOut = port[iPortNameR]
                elif port[iPortGroupId] == gIn and port[iPortId] == pIn:
                    portRealNameIn = port[iPortNameR]

            if portRealNameOut and portRealNameIn:
                jacklib.disconnect(gJack.client, portRealNameOut, portRealNameIn)

    def initPorts(self):
        self.fGroupList      = []
        self.fGroupSplitList = []
        self.fPortList       = []
        self.fConnectionList = []

        self.fLastGroupId = 1
        self.fLastPortId  = 1
        self.fLastConnectionId = 1

        self.initJackPorts()

    def initJack(self):
        self.fXruns = 0
        self.fNextSampleRate = 0.0

        self.fLastBPM = None
        self.fLastTransportState = None

        bufferSize = int(jacklib.get_buffer_size(gJack.client))
        sampleRate = int(jacklib.get_sample_rate(gJack.client))
        realtime   = bool(int(jacklib.is_realtime(gJack.client)))

        self.ui_setBufferSize(bufferSize)
        self.ui_setSampleRate(sampleRate)
        self.ui_setRealTime(realtime)
        self.ui_setXruns(0)

        self.refreshDSPLoad()
        self.refreshTransport()

        self.initJackCallbacks()
        self.initJackPorts()

        self.scene.zoom_fit()
        self.scene.zoom_reset()

        jacklib.activate(gJack.client)

    def initJackCallbacks(self):
        jacklib.set_buffer_size_callback(gJack.client, self.JackBufferSizeCallback, None)
        jacklib.set_sample_rate_callback(gJack.client, self.JackSampleRateCallback, None)
        jacklib.set_xrun_callback(gJack.client, self.JackXRunCallback, None)
        jacklib.set_port_registration_callback(gJack.client, self.JackPortRegistrationCallback, None)
        jacklib.set_port_connect_callback(gJack.client, self.JackPortConnectCallback, None)
        jacklib.set_property_change_callback(gJack.client, self.JackPropertyChangeCallback, None)
        jacklib.on_shutdown(gJack.client, self.JackShutdownCallback, None)

        jacklib.set_client_rename_callback(gJack.client, self.JackClientRenameCallback, None)
        jacklib.set_port_rename_callback(gJack.client, self.JackPortRenameCallback, None)

    def initJackPorts(self):
        if not gJack.client:
            return

        # Get all jack ports
        portNameList = c_char_p_p_to_list(jacklib.get_ports(gJack.client, "", "", 0))

        # Add jack ports
        for portName in portNameList:
            portPtr = jacklib.port_by_name(gJack.client, portName)
            self.canvas_addJackPort(portPtr, portName)

        # Add jack connections
        for portName in portNameList:
            portPtr = jacklib.port_by_name(gJack.client, portName)

            # Only make connections from an output port
            if jacklib.port_flags(portPtr) & jacklib.JackPortIsInput:
                continue

            portConnectionNames = tuple(jacklib.port_get_all_connections(gJack.client, portPtr))

            if portConnectionNames:
                for portConName in portConnectionNames:
                    self.canvas_connectPortsByName(portName, portConName)

    def canvas_getGroupId(self, groupName):
        for group in self.fGroupList:
            if group[iGroupName] == groupName:
                return group[iGroupId]
        return -1

    def canvas_getGroupName(self, groupId):
        for group in self.fGroupList:
            if group[iGroupId] == groupId:
                return group[iGroupName]
        return ""

    def canvas_addJackGroup(self, groupName):
        props = jacklib.get_client_properties(gJack.client, groupName)

        groupId    = self.fLastGroupId
        groupSplit = patchcanvas.SPLIT_UNDEF
        groupIcon  = patchcanvas.ICON_APPLICATION
        groupPos   = ""

        for prop in props:
            if prop.key == URI_POSITION:
                groupPos = prop.value
            elif prop.key == URI_PLUGIN_ICON:
                print("plugin icon is", prop.value)
            elif prop.key == URI_PLUGIN_ID:
                groupIcon = patchcanvas.ICON_PLUGIN

            #if iconName == "hardware":
                #groupSplit = patchcanvas.SPLIT_YES
                #groupIcon  = patchcanvas.ICON_HARDWARE
            ##elif iconName =="carla":
                ##groupIcon = patchcanvas.ICON_CARLA
            #elif iconName =="distrho":
                #groupIcon = patchcanvas.ICON_DISTRHO
            #elif iconName =="file":
                #groupIcon = patchcanvas.ICON_FILE
            #elif iconName =="plugin":
                #groupIcon = patchcanvas.ICON_PLUGIN

        if groupPos:
            x1, y1, x2, y2 = tuple(int(v) for v in groupPos.split(":",4))
            groupSplit = (x1 != 0 and x2 != 0) or (y1 != 0 and y2 != 0)

        patchcanvas.addGroup(groupId, groupName, groupSplit, groupIcon)

        if groupPos:
            if groupSplit:
                patchcanvas.splitGroup(groupId)
            else:
                patchcanvas.joinGroup(groupId)
            patchcanvas.setGroupPosFull(groupId, x1, y1, x2, y2)

        groupObj = [None, None]
        groupObj[iGroupId]   = groupId
        groupObj[iGroupName] = groupName

        self.fGroupList.append(groupObj)
        self.fLastGroupId += 1

        return groupId

    def canvas_removeGroup(self, groupName):
        groupId = -1
        for group in self.fGroupList:
            if group[iGroupName] == groupName:
                groupId = group[iGroupId]
                self.fGroupList.remove(group)
                break
        else:
            print("Catia - remove group failed")
            return

        patchcanvas.removeGroup(groupId)

    def canvas_addJackPort(self, portPtr, portName):
        portId  = self.fLastPortId
        groupId = -1

        portNameR = portName

        aliasN = self.fSavedSettings["Main/JackPortAlias"]
        if aliasN in (1, 2):
            aliases = jacklib.port_get_aliases(portPtr)
            if aliases[0] == 2 and aliasN == 2:
                portName = aliases[2]
            elif aliases[0] >= 1 and aliasN == 1:
                portName = aliases[1]

        portFlags = jacklib.port_flags(portPtr)
        groupName = portName.split(":", 1)[0]

        if portFlags & jacklib.JackPortIsInput:
            portMode = patchcanvas.PORT_MODE_INPUT
        elif portFlags & jacklib.JackPortIsOutput:
            portMode = patchcanvas.PORT_MODE_OUTPUT
        else:
            portMode = patchcanvas.PORT_MODE_NULL

        portShortName = portName.replace("%s:" % groupName, "", 1)

        portTypeStr = jacklib.port_type(portPtr)
        if portTypeStr == jacklib.JACK_DEFAULT_AUDIO_TYPE:
            portType = patchcanvas.PORT_TYPE_AUDIO_JACK
        elif portTypeStr == jacklib.JACK_DEFAULT_MIDI_TYPE:
            portType = patchcanvas.PORT_TYPE_MIDI_JACK
        else:
            portType = patchcanvas.PORT_TYPE_NULL

        for group in self.fGroupList:
            if group[iGroupName] == groupName:
                groupId = group[iGroupId]
                break
        else:
            # For ports with no group
            groupId = self.canvas_addJackGroup(groupName)

        patchcanvas.addPort(groupId, portId, portShortName, portMode, portType)

        portObj = [None, None, None, None, None]
        portObj[iPortId]        = portId
        portObj[iPortName]      = portName
        portObj[iPortNameR]     = portNameR
        portObj[iPortGroupId]   = groupId
        portObj[iPortGroupName] = groupName

        self.fPortList.append(portObj)
        self.fLastPortId += 1

        if groupId not in self.fGroupSplitList and (portFlags & jacklib.JackPortIsPhysical) > 0:
            patchcanvas.splitGroup(groupId)
            patchcanvas.setGroupIcon(groupId, patchcanvas.ICON_HARDWARE)
            self.fGroupSplitList.append(groupId)

        return portId

    def canvas_removeJackPort(self, groupId, portId):
        patchcanvas.removePort(groupId, portId)

        for port in self.fPortList:
            if port[iPortId] == portId and port[iPortGroupId] == groupId:
                groupName = port[iPortGroupName]
                self.fPortList.remove(port)
                break
        else:
            return

        # Check if group has no more ports; if yes remove it
        for port in self.fPortList:
            if port[iPortGroupName] == groupName:
                break
        else:
            self.canvas_removeGroup(groupName)

    def canvas_renamePort(self, groupId, portId, portShortName):
        patchcanvas.renamePort(groupId, portId, portShortName)

    def canvas_connectPorts(self, outGroupId, outPortId, inGroupId, inPortId):
        connectionId = self.fLastConnectionId
        patchcanvas.connectPorts(connectionId, outGroupId, outPortId, inGroupId, inPortId)

        connObj = [None, None, None, None, None]
        connObj[iConnId]       = connectionId
        connObj[iConnOutGroup] = outGroupId
        connObj[iConnOutPort]  = outPortId
        connObj[iConnInGroup]  = inGroupId
        connObj[iConnInPort]   = inPortId

        self.fConnectionList.append(connObj)
        self.fLastConnectionId += 1

        return connectionId

    def canvas_connectPortsByName(self, portOutName, portInName):
        outGroupId = outPortId = inGroupId = inPortId = -1

        for port in self.fPortList:
            if port[iPortNameR] == portOutName:
                outPortId = port[iPortId]
                outGroupId = port[iPortGroupId]
            elif port[iPortNameR] == portInName:
                inPortId = port[iPortId]
                inGroupId = port[iPortGroupId]

            if outPortId >= 0 and inPortId >= 0:
                break

        else:
            print("Catia - connect jack ports failed")
            return -1

        return self.canvas_connectPorts(outGroupId, outPortId, inGroupId, inPortId)

    def canvas_disconnectPorts(self, outGroupId, outPortId, inGroupId, inPortId):
        for connection in self.fConnectionList:
            if connection[iConnOutGroup] != outGroupId:
                continue
            if connection[iConnOutPort] != outPortId:
                continue
            if connection[iConnInGroup] != inGroupId:
                continue
            if connection[iConnInPort] != inPortId:
                continue
            patchcanvas.disconnectPorts(connection[iConnId])
            self.fConnectionList.remove(connection)
            break

    def canvas_disconnectPortsByName(self, portOutName, portInName):
        outGroupId = outPortId = inGroupId = inPortId = -1

        for port in self.fPortList:
            if port[iPortNameR] == portOutName:
                outPortId = port[iPortId]
                outGroupId = port[iPortGroupId]
            elif port[iPortNameR] == portInName:
                inPortId = port[iPortId]
                inGroupId = port[iPortGroupId]

            if outPortId >= 0 and inPortId >= 0:
                break

        else:
            print("Catia - disconnect ports failed")
            return

        self.canvas_disconnectPorts(outGroupId, outPortId, inGroupId, inPortId)

    def jackStarted(self):
        if not gJack.client:
            gJack.client = jacklib.client_open("catia", jacklib.JackNoStartServer, None)
            if not gJack.client:
                self.jackStopped()
                return False

        self.menuJackTransport(True)

        self.ui.cb_buffer_size.setEnabled(True)
        self.ui.cb_sample_rate.setEnabled(True)

        self.ui.pb_dsp_load.setMaximum(100)
        self.ui.pb_dsp_load.setValue(0)
        self.ui.pb_dsp_load.update()

        self.initJack()

        return True

    def jackStopped(self):
        # client already closed
        gJack.client = None

        # refresh canvas (remove jack ports)
        patchcanvas.clear()
        self.initPorts()

        self.ui.cb_buffer_size.setEnabled(False)
        self.ui.cb_sample_rate.setEnabled(False)

        self.menuJackTransport(False)
        self.ui_setXruns(-1)

        if self.fCurTransportView == TRANSPORT_VIEW_HMS:
            self.ui.label_time.setText("00:00:00")
        elif self.fCurTransportView == TRANSPORT_VIEW_BBT:
            self.ui.label_time.setText("000|0|0000")
        elif self.fCurTransportView == TRANSPORT_VIEW_FRAMES:
            self.ui.label_time.setText("000'000'000")

        self.ui.pb_dsp_load.setValue(0)
        self.ui.pb_dsp_load.setMaximum(0)
        self.ui.pb_dsp_load.update()

    def menuJackTransport(self, enabled):
        self.ui.act_transport_play.setEnabled(enabled)
        self.ui.act_transport_stop.setEnabled(enabled)
        self.ui.act_transport_backwards.setEnabled(enabled)
        self.ui.act_transport_forwards.setEnabled(enabled)
        self.ui.menu_Transport.setEnabled(enabled)
        self.ui.group_transport.setEnabled(enabled)

    def JackXRunCallback(self, arg):
        if DEBUG: print("JackXRunCallback()")
        self.XRunCallback.emit()
        return 0

    def JackBufferSizeCallback(self, bufferSize, arg):
        if DEBUG: print("JackBufferSizeCallback(%i)" % bufferSize)
        self.BufferSizeCallback.emit(bufferSize)
        return 0

    def JackSampleRateCallback(self, sampleRate, arg):
        if DEBUG: print("JackSampleRateCallback(%i)" % sampleRate)
        self.SampleRateCallback.emit(sampleRate)
        return 0

    def JackClientRenameCallback(self, oldName, newName, arg):
        if DEBUG: print("JackClientRenameCallback(\"%s\", \"%s\")" % (oldName, newName))
        self.ClientRenameCallback.emit(str(oldName, encoding="utf-8"), str(newName, encoding="utf-8"))
        return 0

    def JackPortRegistrationCallback(self, portId, registerYesNo, arg):
        if DEBUG: print("JackPortRegistrationCallback(%i, %i)" % (portId, registerYesNo))
        self.PortRegistrationCallback.emit(portId, bool(registerYesNo))
        return 0

    def JackPortConnectCallback(self, portA, portB, connectYesNo, arg):
        if DEBUG: print("JackPortConnectCallback(%i, %i, %i)" % (portA, portB, connectYesNo))
        self.PortConnectCallback.emit(portA, portB, bool(connectYesNo))
        return 0

    def JackPortRenameCallback(self, portId, oldName, newName, arg):
        if DEBUG: print("JackPortRenameCallback(%i, \"%s\", \"%s\")" % (portId, oldName, newName))
        self.PortRenameCallback.emit(portId, str(oldName, encoding="utf-8"), str(newName, encoding="utf-8"))
        return 0

    def JackPropertyChangeCallback(self, uuid, key, change, arg):
        if DEBUG: print("PropertyChangeCallback(%i, %s, %i)" % (uuid, key, change))
        self.PropertyChangeCallback.emit(jacklib.jack_uuid_t(uuid), str(key, encoding="utf-8"), change)
        return 0

    def JackShutdownCallback(self, arg):
        if DEBUG: print("JackShutdownCallback()")
        self.ShutdownCallback.emit()
        return 0

    @pyqtSlot()
    def slot_JackClearXruns(self):
        if gJack.client:
            self.fXruns = 0
            self.ui_setXruns(0)

    @pyqtSlot()
    def slot_XRunCallback(self):
        self.fXruns += 1
        self.ui_setXruns(self.fXruns)

    @pyqtSlot(int)
    def slot_BufferSizeCallback(self, bufferSize):
        self.ui_setBufferSize(bufferSize)

    @pyqtSlot(int)
    def slot_SampleRateCallback(self, sampleRate):
        self.ui_setSampleRate(sampleRate)

        self.ui_setRealTime(bool(int(jacklib.is_realtime(gJack.client))))
        self.ui_setXruns(0)

    @pyqtSlot(str, str)
    def slot_ClientRenameCallback(self, oldName, newName):
        pass # TODO

    @pyqtSlot(int, bool)
    def slot_PortRegistrationCallback(self, portIdJack, registerYesNo):
        portPtr = jacklib.port_by_id(gJack.client, portIdJack)
        portNameR = jacklib.port_name(portPtr)

        if registerYesNo:
            self.canvas_addJackPort(portPtr, portNameR)
        else:
            for port in self.fPortList:
                if port[iPortNameR] == portNameR:
                    portIdCanvas = port[iPortId]
                    groupId = port[iPortGroupId]
                    break
            else:
                return

            self.canvas_removeJackPort(groupId, portIdCanvas)

    @pyqtSlot(int, int, bool)
    def slot_PortConnectCallback(self, portIdJackA, portIdJackB, connectYesNo):
        portPtrA = jacklib.port_by_id(gJack.client, portIdJackA)
        portPtrB = jacklib.port_by_id(gJack.client, portIdJackB)
        portRealNameA = jacklib.port_name(portPtrA)
        portRealNameB = jacklib.port_name(portPtrB)

        if connectYesNo:
            self.canvas_connectPortsByName(portRealNameA, portRealNameB)
        else:
            self.canvas_disconnectPortsByName(portRealNameA, portRealNameB)

    @pyqtSlot(int, str, str)
    def slot_PortRenameCallback(self, portIdJack, oldName, newName):
        portPtr = jacklib.port_by_id(gJack.client, portIdJack)
        portShortName = jacklib.port_short_name(portPtr)

        for port in self.fPortList:
            if port[iPortNameR] == oldName:
                portIdCanvas = port[iPortId]
                groupId = port[iPortGroupId]
                port[iPortNameR] = newName
                break
        else:
            return

        # Only set new name in canvas if no alias is active for this port
        aliases = jacklib.port_get_aliases(portPtr)
        if aliases[0] == 1 and self.fSavedSettings["Main/JackPortAlias"] == 1:
            pass
        elif aliases[0] == 2 and self.fSavedSettings["Main/JackPortAlias"] == 2:
            pass
        else:
            self.canvas_renamePort(groupId, portIdCanvas, portShortName)

    @pyqtSlot(jacklib.jack_uuid_t, str, int)
    def slot_PropertyChangeCallback(self, uuid, key, change):
        if key != URI_POSITION:
            return

        prop = jacklib.get_property(uuid, key)

        if prop is None:
          return

        x1, y1, x2, y2 = tuple(int(v) for v in prop.value.split(":",4))

        clientName = jacklib.get_client_name_by_uuid(gJack.client, jacklib.uuid_unparse(uuid))

        if not clientName:
            return

        groupId = self.canvas_getGroupId(jacklib._d(clientName))

        if groupId == -1:
            return

        if (x1 != 0 and x2 != 0) or (y1 != 0 and y2 != 0):
            patchcanvas.splitGroup(groupId)
        else:
            patchcanvas.joinGroup(groupId)
        patchcanvas.setGroupPosFull(groupId, x1, y1, x2, y2)

    @pyqtSlot()
    def slot_ShutdownCallback(self):
        self.jackStopped()

    @pyqtSlot()
    def slot_configureCatia(self):
        dialog = SettingsW(self, "catia", hasGL)
        if dialog.exec_():
            self.loadSettings(False)
            patchcanvas.clear()

            pOptions = patchcanvas.options_t()
            pOptions.theme_name        = self.fSavedSettings["Canvas/Theme"]
            pOptions.auto_hide_groups  = self.fSavedSettings["Canvas/AutoHideGroups"]
            pOptions.use_bezier_lines  = self.fSavedSettings["Canvas/UseBezierLines"]
            pOptions.antialiasing      = self.fSavedSettings["Canvas/Antialiasing"]
            pOptions.eyecandy          = self.fSavedSettings["Canvas/EyeCandy"]
            pOptions.auto_select_items = False # TODO
            pOptions.inline_displays   = False

            pFeatures = patchcanvas.features_t()
            pFeatures.group_info   = False
            pFeatures.group_rename = False
            pFeatures.port_info    = True
            pFeatures.port_rename  = bool(self.fSavedSettings["Main/JackPortAlias"] > 0)
            pFeatures.handle_group_pos = True

            patchcanvas.setOptions(pOptions)
            patchcanvas.setFeatures(pFeatures)
            patchcanvas.init("Catia", self.scene, self.canvasCallback, DEBUG)

            self.initPorts()

    @pyqtSlot()
    def slot_aboutCatia(self):
        QMessageBox.about(self, self.tr("About Catia"), self.tr("<h3>Catia</h3>"
                                                                "<br>Version %s"
                                                                "<br>Catia is a simple JACK Patchbay.<br>"
                                                                "<br>Copyright (C) 2010-2020 falkTX" % VERSION))

    def saveSettings(self):
        settings = QSettings()

        settings.setValue("Geometry", self.saveGeometry())
        settings.setValue("ShowToolbar",  self.ui.act_settings_show_toolbar.isChecked())
        settings.setValue("ShowStatusbar", self.ui.act_settings_show_statusbar.isChecked())
        settings.setValue("TransportView", self.fCurTransportView)

    def loadSettings(self, geometry):
        settings = QSettings()

        if geometry:
            self.restoreGeometry(settings.value("Geometry", b""))

            showToolbar = settings.value("ShowToolbar", True, type=bool)
            self.ui.act_settings_show_toolbar.setChecked(showToolbar)
            self.ui.frame_toolbar.setVisible(showToolbar)

            showStatusbar = settings.value("ShowStatusbar", True, type=bool)
            self.ui.act_settings_show_statusbar.setChecked(showStatusbar)
            self.ui.frame_statusbar.setVisible(showStatusbar)

            self.setTransportView(settings.value("TransportView", TRANSPORT_VIEW_HMS, type=int))

        self.fSavedSettings = {
            "Main/RefreshInterval": settings.value("Main/RefreshInterval", 120, type=int),
            "Main/JackPortAlias": settings.value("Main/JackPortAlias", 2, type=int),
            "Canvas/Theme": settings.value("Canvas/Theme", patchcanvas.getDefaultThemeName(), type=str),
            "Canvas/AutoHideGroups": settings.value("Canvas/AutoHideGroups", False, type=bool),
            "Canvas/UseBezierLines": settings.value("Canvas/UseBezierLines", True, type=bool),
            "Canvas/EyeCandy": settings.value("Canvas/EyeCandy", patchcanvas.EYECANDY_SMALL, type=int),
            "Canvas/UseOpenGL": settings.value("Canvas/UseOpenGL", False, type=bool),
            "Canvas/Antialiasing": settings.value("Canvas/Antialiasing", patchcanvas.ANTIALIASING_SMALL, type=int),
            "Canvas/HighQualityAntialiasing": settings.value("Canvas/HighQualityAntialiasing", False, type=bool)
        }

    def timerEvent(self, event):
        if event.timerId() == self.fTimer120:
            if gJack.client:
                self.refreshTransport()
        elif event.timerId() == self.fTimer600:
            if gJack.client:
                self.refreshDSPLoad()
        QMainWindow.timerEvent(self, event)

    def closeEvent(self, event):
        self.saveSettings()
        patchcanvas.clear()
        QMainWindow.closeEvent(self, event)

# ------------------------------------------------------------------------------------------------------------
# Main

if __name__ == '__main__':
    # App initialization
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("Catia")
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Cadence")
    app.setWindowIcon(QIcon(":/scalable/catia.svg"))

    if jacklib is None:
        QMessageBox.critical(None,
                             app.translate("CatiaMainW", "Error"),
                             app.translate("CatiaMainW",
                                           "JACK is not available in this system, cannot use this application."))
        sys.exit(1)

    # Init GUI
    gui = CatiaMainW()

    # Set-up custom signal handling
    setUpSignals(gui)

    # Show GUI
    gui.show()

    # App-Loop
    ret = app.exec_()

    # Close Jack
    if gJack.client:
        jacklib.deactivate(gJack.client)
        jacklib.client_close(gJack.client)

    # Exit properly
    sys.exit(ret)
