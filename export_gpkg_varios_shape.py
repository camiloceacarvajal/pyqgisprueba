from qgis.utils import iface
from qgis.core import *
from qgis.PyQt.QtWidgets import *
from PyQt5.QtCore import *
from processing.tools import dataobjects
import datetime,random, processing,os,sys
nameprefix = ""
AskTimeStamp = False
gpkg_filename = "M20_20220206.gpkg"
def printl(message):
   print(message)   
   QApplication.processEvents()
def remove_field(rlayer, rfield):
    fieldname = rfield
    if rlayer.dataProvider().fieldNameIndex(fieldname) != -1:
      #printl('Deleting existing field '+fieldname)
      rlayer.dataProvider().deleteAttributes([rlayer.dataProvider().fieldNameIndex(fieldname)])
    rlayer.updateFields() #propagate field update
def find_majority(k):
    myMap = {}
    maximum = ( '', 0 ) # (occurring element, occurrences)
    for n in k:
        if n in myMap: myMap[n] += 1
        else: myMap[n] = 1
        # Keep track of maximum on the go
        if myMap[n] > maximum[1]: maximum = (n,myMap[n])
    return maximum
def group_iterate(group): ## return all layers in group and subgroups 
    return_layers = []
    if not isinstance(group, QgsLayerTreeGroup):
        #raise Exception(group.name() + " is not a layer group! Aborting")        
        printl(group.name() + " is not a layer group! Aborting")
        return []
    printl('Group: '+group.name())
    for c in group.children():        
        if isinstance(c, QgsLayerTreeGroup):
            return_layers.extend(group_iterate(c))
        else: # layer, not group
            printl(' -> ' + c.name())
            return_layers.append(c.layer())
    return return_layers
def all_geopackage(self):
    ####### CHOOSE DIRECTORY
    global sself
    sself = self
    printl('geopackage init')
    layers = [layer for layer in QgsProject.instance().mapLayers().values()]
    memlayercount = 0
    for layer in layers:
        #luri = layer.dataProvider().dataSourceUri()
        if layer.type() == QgsMapLayer.VectorLayer: memlayercount += 1
    printl("Vector layers: "+str(memlayercount))
    if memlayercount == 0:
      #raise Exception("No vector layers to save")
      printl("No vector layers to save")
      return
    timestamp = False
    if AskTimeStamp:  
        buttonReply = QMessageBox.question(iface.mainWindow(), 'Kérdés', "Legyen timestamp a filenevekben?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            timestamp=True
        printl("Timestamp: "+str(timestamp))
    pathlist = []
    allprojectlayers = [layer for layer in QgsProject.instance().mapLayers().values()]
    for layer in allprojectlayers:
        path = os.path.dirname(layer.dataProvider().dataSourceUri())
        if path != "": pathlist.append(path)
    path = QgsExpressionContextUtils.projectScope(QgsProject.instance()).variable('save_layerpath')
    if path == NULL:
        path = ""   
        path = find_majority(pathlist)
        printl("Guessed save path: "+path[0])
        path = os.path.join(path[0].replace('/','\\'), '')
    else:
        printl("Stored save path: "+path)
        path = os.path.join(path.replace('/','\\'), '')
        
    qid = QInputDialog()
    path, ok = QInputDialog.getText(qid, "GPKG filename", "GPKG filename: ",  QLineEdit.Normal,path+gpkg_filename)
    #path = os.path.join(path.replace('/','\\'), '')
    if ok is not True:
      #raise Exception("Dir cancel ")
      printl("Dir cancel")
      return
    ########## TODO
    #layer.dataProvider().dataSourceUri ()
    #layer.dataProvider().dataSourceUri() / 'memory?geometry=MultiPolygon&crs=EPSG:23700'
    #s.startswith('memory?') 
    namemap = {}
    lnamemap = {}
    gpkg_name = path #+ gpkg_filename
    qmltemp=QgsProcessingUtils.generateTempFilename('temp.qml')
    lcount = len(layers)
    lnum = 0
    for layer in layers:
        lnum = lnum + 1
        luri = layer.dataProvider().dataSourceUri()
        if layer.type() != QgsMapLayer.VectorLayer:
          continue
        orglayer = layer
        #layer=QgsVectorLayer(layer.dataProvider().dataSourceUri(),layer.name() ,"postgres") # load without virtual fields
        lname = layer.name()
        field_names = [field.name() for field in layer.dataProvider().fields() ]
        #printl("fixgeometries - "+lname)
        layer.saveNamedStyle(qmltemp)
        layer = processing.run("native:fixgeometries", {'INPUT': layer,'OUTPUT': 'memory:' })['OUTPUT']
        if lname=="":
           printl('Unnamed layer, renaming')
           lname = 'temp_'+str(random.randint(0, 100))  
           while lname in lnamemap:
             lname = 'temp_'+str(random.randint(0, 100))  
        layer.setName(lname)
        layer.loadNamedStyle(qmltemp)
        fix_field_names = [field.name() for field in layer.dataProvider().fields() ]
        for fieldname in fix_field_names:
          if not fieldname in field_names: 
             remove_field(layer,fieldname)
        ## gpkg 
        remove_field(layer,"fid")
        oldname = lname
        if (lname in lnamemap) and (lnamemap[lname]!=luri):
          printl('duplicate layer name: '+lname)
          while lname in lnamemap:
            lname = oldname+'_'+str(random.randint(0, 100)) 
          layer.setName(lname)
          printl('-> new name: '+lname)
        if (not luri in namemap!='') or (luri.startswith('memory?')):
            ido = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M")
            #lname = "".join(x for x in lname if (x=='-' or x=='_' or x.isalnum() or x.isspace()))
            #_writer = QgsVectorFileWriter.writeAsVectorFormat(layer,fname,"utf-8",layer.crs())
            printl("Packaging "+str(lnum) +"/"+str(lcount)+" - "+lname)
            processing.run("native:package", {'LAYERS':[layer],'OUTPUT':gpkg_name,'OVERWRITE':False,'SAVE_STYLES':True})
            #QgsProject.instance().addMapLayer(layer)
            #printl("Saved "+lname)
            namemap[luri]=lname
        else:
            lname = namemap[luri]
            printl("Using existing GPKG layer: "+lname+" for layer "+orglayer.name())
        lnamemap[lname]=luri
        orglayer.setDataSource(gpkg_name+"|layername="+lname,orglayer.name(),"ogr")
    printl('Ready')
## run only from python console    
if __name__ == "__console__":
    all_geopackage(None)  
from qgis.core import QgsProject
QgsProject.instance().removeAllMapLayers()
    
