import npyscreen
import json
import os

from whatnot import login_and_save_session

JSON_FILEPATH = ""

def load_data():
    with open(JSON_FILEPATH, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(JSON_FILEPATH, 'w') as f:
        json.dump(data, f, indent=4)

class CameraEditor(npyscreen.FormBaseNew):
    def create(self):
        self.add(npyscreen.FixedText, value="Camera List (Press A: Add, E: Edit, D: Delete, Q: Quit, V: Edit Env)", editable=False)
        self.camera_list = self.add(npyscreen.SelectOne, max_height=10, scroll_exit=True)
        self.update_list()

        # Add key handlers here
        self.add_handlers({
            'a': self.add_camera,
            'e': self.edit_camera,
            'd': self.delete_camera,
            'q': self.quit_app,
            'v': self.edit_env,
        })

    def update_list(self):
        # Load the updated data
        self.parentApp.camera_data = load_data()

        # Explicitly clear the camera list widget
        self._clear_all_widgets()
        self.add(npyscreen.FixedText, value="📸 Camera List (Press A: Add, E: Edit, D: Delete, Q: Quit, V: Edit Env)", editable=False)
        self.camera_list = self.add(npyscreen.SelectOne, max_height=10, scroll_exit=True)
        
        # Forcefully reinitialize the widget to clear any residual artifacts
        self.camera_list.values = [f"{i+1}. {c['name']}" for i, c in enumerate(self.parentApp.camera_data)]
        self.camera_list.value = None  # Reset selection for non-empty lists
        self.camera_list.display()

    def add_camera(self, *args):
        self.parentApp.getForm('EDIT').index = None
        self.parentApp.switchForm('EDIT')

    def edit_camera(self, *args):
        idxs = self.camera_list.value
        if idxs:
            self.parentApp.getForm('EDIT').index = idxs[0]
            self.parentApp.switchForm('EDIT')

    def delete_camera(self, *args):
        idxs = self.camera_list.value
        if idxs:
            idx = idxs[0]
            name = self.parentApp.camera_data[idx]['name']
            if npyscreen.notify_yes_no(f"Delete '{name}'?", title="Confirm", editw=2):
                # Delete the selected camera
                self.parentApp.camera_data.pop(idx)

                save_data(self.parentApp.camera_data)

                self.parentApp.camera_data = load_data()
                
                # Forcefully reinitialize the widget to clear any residual artifacts
                self.camera_list.values = [f"{i+1}. {c['name']}" for i, c in enumerate(self.parentApp.camera_data)]
                self.camera_list.value = []  # Reset selection for non-empty lists
                self.camera_list.display()
                
    def quit_app(self, *args):
        self.parentApp.setNextForm(None)
        self.editing = False
        self.parentApp.switchFormNow()

    def edit_env(self, *args):
        self.parentApp.switchForm("ENV")

class EditCameraForm(npyscreen.ActionForm):
    def create(self):
        self.name = self.add(npyscreen.TitleText, name="Name:")
        self.link = self.add(npyscreen.TitleText, name="Link:")
        self.description = self.add(npyscreen.TitleText, name="Description:")
        self.index = None

    def beforeEditing(self):
        if self.index is not None:
            cam = self.parentApp.camera_data[self.index]
            self.name.value = cam.get("name", "")
            self.link.value = cam.get("link", "")
            self.description.value = cam.get("description", "")
        else:
            self.name.value = ""
            self.link.value = ""
            self.description.value = ""

    def on_ok(self):
        if not all([self.name.value.strip(), self.link.value.strip(), self.description.value.strip()]):
            npyscreen.notify_confirm("All fields are required!", title="Error", editw=2)
            return

        new_data = {
            "name": self.name.value.strip(),
            "link": self.link.value.strip(),
            "description": self.description.value.strip()
        }

        if self.index is not None:
            self.parentApp.camera_data[self.index] = new_data
        else:
            self.parentApp.camera_data.append(new_data)

        save_data(self.parentApp.camera_data)

        # Update the main screen list and reset selection
        main_form = self.parentApp.getForm("MAIN")
        main_form.update_list()

        # Switch back to the main form
        self.parentApp.switchForm("MAIN")
    def on_cancel(self):
        self.parentApp.switchForm("MAIN")

class EditEnvForm(npyscreen.ActionForm):
    def create(self):
        self.env_vars = {}
        self.env_widgets = []

    def beforeEditing(self):
        # Load environment variables from the .env file
        from dotenv import dotenv_values
        self.env_vars = dotenv_values(".env")

        # Clear existing widgets
        self._clear_all_widgets()

        # Add widgets for each environment variable
        self.env_widgets = []
        for key, value in self.env_vars.items():
            widget = self.add(npyscreen.TitleText, name=f"{key}:", value=value)
            self.env_widgets.append((key, widget))

    def on_ok(self):
        # Save updated environment variables to the .env file
        updated_env_vars = {key: widget.value for key, widget in self.env_widgets}
        with open(".env", "w") as f:
            for key, value in updated_env_vars.items():
                f.write(f'{key}="{value}"\n')

        npyscreen.notify_confirm("Environment variables updated!", title="Success", editw=2)
        self.parentApp.switchForm("MAIN")

    def on_cancel(self):
        self.parentApp.switchForm("MAIN")

class CameraApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.camera_data = load_data()
        self.addForm("MAIN", CameraEditor, name="Camera Manager")
        self.addForm("EDIT", EditCameraForm, name="Edit Camera")
        self.addForm("ENV", EditEnvForm, name="Edit Environment Variables") 

if __name__ == "__main__":
    JSON_FILEPATH = "data.json"

    if not os.path.exists(JSON_FILEPATH):
        with open(JSON_FILEPATH, 'w') as f:
            json.dump([], f)

    app = CameraApp()
    app.run()
    from dotenv import load_dotenv
    load_dotenv()
    phone_num = os.getenv('PHONE_NUM')
    print(f"Now you need to manually login to WhatsApp Web({phone_num}) using the provided code. Please wait for it.")
    login_and_save_session(phone_num)
