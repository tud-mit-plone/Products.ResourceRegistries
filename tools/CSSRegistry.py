from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager

from Products.CMFCore.utils import UniqueObject, getToolByName
from Products.CMFCore.ActionProviderBase import ActionProviderBase

from Acquisition import aq_base, aq_parent 

from Products.CSSRegistry import config
from Products.CSSRegistry import permissions
from Products.CSSRegistry.interfaces import ICSSRegistry

from Products.CMFCore.Expression import Expression
from Products.CMFCore.Expression import createExprContext

from OFS.Image import File

import random


class CSSRegistryTool(UniqueObject, SimpleItem, PropertyManager):
    """An example tool.
    """

    id = config.TOOLNAME
    meta_type = config.TOOLTYPE

    security = ClassSecurityInfo()

    #__implements__ = (ActionProviderBase.__implements__,)
    __implements__ = (SimpleItem.__implements__, ICSSRegistry,)

    def __init__(self ):
        """ add the storages """
        self.stylesheets = ()
        self.cookedstylesheets = ()
        self.concatenatedstylesheets = {}
        self.scripts = ()
        self.cookedscripts = ()

    security.declareProtected(permissions.ManagePortal, 'registerStylesheet')
    def registerStylesheet(self, id, expression='', media='', rel='stylesheet', cssimport=0, inline=0, enabled=1 ):
        """ register a stylesheet"""
        stylesheet = {}
        stylesheet['id'] = id
        stylesheet['expression'] = expression 
        stylesheet['media'] = media
        stylesheet['rel'] = rel 
        stylesheet['cssimport'] = cssimport
        stylesheet['inline'] = inline
        stylesheet['enabled'] = enabled
        self.storeStylesheet(stylesheet )

    security.declareProtected(permissions.ManagePortal, 'registerScript')
    def registerScript(self, id, expression='', contenttype='text/javascript', inline=0, enabled=1):
        """ register a script"""
        script = {}
        script['id'] = id
        script['expression'] = expression 
        script['contenttype'] = media
        script['inline'] = inline
        script['enabled'] = enabled
        self.storeScript(script)


    security.declarePrivate('validateId')
    def validateId(self, id, existing):
        """ safeguard against dulicate ids"""
        for sheet in existing:
            if sheet.get('id') == id: 
                raise ValueError, 'Duplicate id %s' %(id)            

        
    security.declarePrivate('storeStylesheet')            
    def storeStylesheet(self, stylesheet ):
        """ tupleize and store a list of styesheets"""        
        self.validateId(stylesheet.get('id'), self.getStylesheets())
        stylesheets = list(self.stylesheets)
        if len(stylesheets) and stylesheets[0].get('id') == 'ploneCustom.css':
            stylesheets.insert(1, stylesheet)
        else:
            stylesheets.insert(0, stylesheet )
        
        self.stylesheets = tuple(stylesheets)
        self.cookStylesheets()


    security.declarePrivate('storeScript')            
    def storeScript(self, script ):
        """ store a script"""        
        self.validateId(script.get('id'), self.getScripts())
        scripts = list(self.scripts)
        if len(scripts) and scripts[0].get('id') == 'ploneCustom.css':
            scripts.insert(1, script)
        else:
            scripts.insert(0, script )
        self.scripts = tuple(scripts)
        self.cookScripts()

    
    security.declareProtected(permissions.ManagePortal, 'getStylesheets')
    def getStylesheets(self ):
        """ sdf """
        return tuple([item.copy() for item in self.stylesheets])
        
    security.declareProtected(permissions.ManagePortal, 'unregisterStylesheet')        
    def unregisterStylesheet(self, id ):
        """ unreginster a registered stylesheet """
        stylesheets = [ item for item in self.getStylesheets() if item.get('id') != id ]
        self.stylesheets = tuple(stylesheets)
        self.cookStylesheets()
        
    
    def compareStylesheets(self, sheet1, sheet2 ):
        for attr in ('expression', 'media', 'rel', 'cssimport', 'inline'):
            if sheet1.get(attr) != sheet2.get(attr):
                return 0
        return 1
                            
    def generateId(self):
        base = "ploneStyles"
        appendix = ".css"
        return "%s%04d%s" % (base, random.randint(0, 9999), appendix)
                            
    def cookStylesheets(self ):
        stylesheets = self.getStylesheets()
        self.concatenatedstylesheets = {}
        self.cookedstylesheets = ()
        results = []
        for stylesheet in stylesheets:
            #self.concatenatedstylesheets[stylesheet['id']] = [stylesheet['id']]
            if results:
                previtem = results[-1]
                if self.compareStylesheets(stylesheet, previtem):
                    previd = previtem.get('id')
        
                    if self.concatenatedstylesheets.has_key(previd):
                        self.concatenatedstylesheets[previd].append(stylesheet.get('id'))
                    else:
                        magicId = self.generateId()
                        self.concatenatedstylesheets[magicId] = [previd, stylesheet.get('id')]
                        previtem['id'] = magicId
                else:
                    results.append(stylesheet)    
            else:
                results.append(stylesheet)
        #for entry in self.concatenatedstylesheets.:
            
            
        stylesheets = self.getStylesheets()
        for stylesheet in stylesheets:
            self.concatenatedstylesheets[stylesheet['id']] = [stylesheet['id']]
        self.cookedstylesheets = tuple(results)
        
        
    security.declareProtected(permissions.View, 'getEvaluatedStyleheets')        
    def getEvaluatedStylesheets(self, context ):
        
        results = self.cookedstylesheets
        # filter results by expression
        results = [item for item in results if self.evaluateExpression(item.get('expression'), context )]    
        results.reverse()
        return results
         
    security.declarePrivate('evaluateExpression')
    def evaluateExpression(self, expression, context):
        """
        Evaluate an object's TALES condition to see if it should be 
        displayed
        """
        try:
            if expression and context is not None:
                portal = getToolByName(self, 'portal_url').getPortalObject()
                
                # Find folder (code courtesy of CMFCore.ActionsTool)
                if context is None or not hasattr(context, 'aq_base'):
                    folder = portal
                else:
                    folder = context
                    # Search up the containment hierarchy until we find an
                    # object that claims it's PrincipiaFolderish.
                    while folder is not None:
                        if getattr(aq_base(folder), 'isPrincipiaFolderish', 0):
                            # found it.
                            break
                        else:
                            folder = aq_parent(aq_inner(folder))
                
                __traceback_info__ = (folder, portal, context, expression)
                ec = createExprContext(folder, portal, context)
                return Expression(expression)(ec)
            else:
                return 1
        except AttributeError:
            return 1
        
    
    def __getitem__(self, item):
        """ Return a stylesheet from the registry """
        ids = self.concatenatedstylesheets[item]
        output = ""
        for id in ids:
            obj = getattr(self.aq_parent, id)
            if hasattr(aq_base(obj), 'index_html') and callable(obj.index_html):
                content = obj.index_html(self.REQUEST, self.REQUEST.RESPONSE)
            else:
                content = str(obj)
            
            output += content # This needs to be fixed to render the object first
            
        return File(item, item, output, "text/css").__of__(self)
        
InitializeClass(CSSRegistryTool)