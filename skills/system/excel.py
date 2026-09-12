import win32com.client
import os

SKILL_METADATA = {
    'name': 'excel',
    'version': '2.0.0',
    'actions': ['launch', 'write', 'save', 'read']
}

def get_excel():
    try:
        return win32com.client.GetActiveObject("Excel.Application")
    except:
        return win32com.client.Dispatch("Excel.Application")

def execute(action='launch', **kwargs):
    excel = get_excel()
    if action == 'launch':
        excel.Visible = True
        filepath = kwargs.get('filepath')
        if filepath and os.path.exists(filepath):
            excel.Workbooks.Open(os.path.abspath(filepath))
        else:
            excel.Workbooks.Add()
        return {"status": "success", "message": "Excel launched"}
    
    elif action == 'write':
        cell = kwargs.get('cell')
        value = kwargs.get('value')
        sheet_name = kwargs.get('sheet')
        if not cell:
            return {"status": "error", "message": "Cell coordinate required"}
        try:
            wb = excel.ActiveWorkbook
            if not wb:
                wb = excel.Workbooks.Add()
            sheet = wb.Sheets(sheet_name) if sheet_name else excel.ActiveSheet
            sheet.Range(cell).Value = value
            return {"status": "success", "message": f"Wrote {value} to {cell}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    elif action == 'read':
        cell = kwargs.get('cell')
        sheet_name = kwargs.get('sheet')
        if not cell:
            return {"status": "error", "message": "Cell coordinate required"}
        try:
            wb = excel.ActiveWorkbook
            if not wb:
                return {"status": "error", "message": "No active workbook"}
            sheet = wb.Sheets(sheet_name) if sheet_name else excel.ActiveSheet
            val = sheet.Range(cell).Value
            return {"status": "success", "value": val}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    elif action == 'save':
        filepath = kwargs.get('filepath')
        try:
            wb = excel.ActiveWorkbook
            if not wb:
                return {"status": "error", "message": "No active workbook to save"}
            if filepath:
                wb.SaveAs(os.path.abspath(filepath))
            else:
                wb.Save()
            return {"status": "success", "message": "Workbook saved"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return {"status": "error", "message": f"Unknown action: {action}"}