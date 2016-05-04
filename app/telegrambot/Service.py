from JumpScale import j
import telegram
# from JumpScale.baselib.atyourservice.robot.ActionRequest import *

class ServiceMgmt(object):

    def __init__(self, bot):
        self.bot = bot
        self.rootpath = bot.rootpath
        self.callbacks = bot.question_callbacks

    #helpers
    def _blueprintsPath(self, username, project):
        return '%s/%s/%s/blueprints' % (self.rootpath, username, project)

    def _currentProject(self, username):
        return self.bot.project_mgmt._currentProject(username)

    def _currentProjectPath(self, username):
        return self.bot.project_mgmt._projectPath(username, self.bot.project_mgmt._currentProject(username))

    def _currentBlueprintsPath(self, username):
        return self._blueprintsPath(username, self.bot.project_mgmt._currentProject(username))

    def execute(self, bot, update, services, action):
        username = update.message.from_user.username

        for service in services:
            evt = j.data.models.cockpit_event.Telegram()
            evt.io = 'input'
            evt.action = 'service.execute'
            evt.args = {
                'username': username,
                'chat_id': update.message.chat_id,
                'service': service.key,
                'action': action,
                'project_path': self._currentProjectPath(username),
            }
            self.bot.send_event(evt.to_json())

            # bot.sendMessage(chat_id=update.message.chat_id, text="execute on %s" % service)

    def list(self, bot, update, project):
        username = update.message.from_user.username
        project_path = self._currentProjectPath(username)
        j.atyourservice.basepath = project_path
        services = j.atyourservice.findServices()

        services_list = []
        for service in services:
            services_list.append("- %s" % service.key)

        if len(services_list) <= 0:
            bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, this repository doesn't contains services for now.")
            return

        # def cb(bot, update):
        #     message = update.message
        #     if message.text in services_list:
        #         content = j.sal.fs.fileGetContents(j.sal.fs.joinPaths(blueprint_path, message.text))
        #         text = '```\n%s\n```' % content
        #         bot.sendMessage(chat_id=update.message.chat_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=telegram.ReplyKeyboardHide())
        #     else:
        #         bot.sendMessage(chat_id=update.message.chat_id, text="%s is not a valid Blueprint name" % message.text, reply_markup=telegram.ReplyKeyboardHide())
        # self.callbacks[username] = cb

        # reply_markup = telegram.ReplyKeyboardMarkup([services_list])
        # bot.sendMessage(chat_id=update.message.chat_id, text="Click on the blueprint you want to inspect", reply_markup=reply_markup)
        bot.sendMessage(chat_id=update.message.chat_id, text='\n'.join(services_list))

    def delete(self, bot, update, project, names):
        username = update.message.from_user.username

        # ays uninstall before
        # self._ays_sync(bot, update, args=['do', 'uninstall'])
        # j.actions.resetAll()

        for name in names:
            if name == "*" or name == "all":
                blueprints = j.sal.fs.listFilesInDir(self._currentBlueprintsPath(username))
                for blueprint in blueprints:
                    j.sal.fs.remove(blueprint)

                ln = len(blueprints)
                message = "%d blueprint%s removed" % (ln, "s" if ln > 1 else "")
                bot.sendMessage(chat_id=update.message.chat_id, text=message)

            else:
                blueprint = '%s/%s' % (self._blueprintsPath(username, project), name)

                self.bot.logger.debug('deleting: %s' % blueprint)

                if not j.sal.fs.exists(blueprint):
                    message = "Sorry, I don't find any blueprint named `%s`, you can list them with `/blueprint`" % name
                    bot.sendMessage(chat_id=update.message.chat_id, text=message, parse_mode="Markdown")
                    continue

                j.sal.fs.remove(blueprint)

                message = "Blueprint `%s` removed from `%s`" % (name, project)
                bot.sendMessage(chat_id=update.message.chat_id, text=message, parse_mode="Markdown")

        # cleaning
        j.sal.fs.removeDirTree('%s/alog' % self._currentProjectPath(username))
        j.sal.fs.removeDirTree('%s/recipes' % self._currentProjectPath(username))
        j.sal.fs.removeDirTree('%s/services' % self._currentProjectPath(username))
        j.sal.fs.createDir('%s/services' % self._currentProjectPath(username))

    # UI interaction
    def choose_action(self, bot, update):
        self.callbacks[update.message.from_user.username] = self.dispatch_choice
        choices = ['list', 'execute']
        reply_markup = telegram.ReplyKeyboardMarkup([choices], resize_keyboard=True, one_time_keyboard=True)
        return bot.sendMessage(chat_id=update.message.chat_id, text="What do you want to do ?", reply_markup=reply_markup)

    def dispatch_choice(self, bot, update):
        message = update.message
        username = update.message.from_user.username
        project = self._currentProject(username)
        # if message.text == "add":
            # self.create_prompt(bot, update)
        if message.text == 'list':
            self.list(bot, update, project)
        elif message.text == 'execute':
            self.execute_prompt(bot, update)

    def execute_prompt(self, bot, update):
        username = update.message.from_user.username

        def select_action(bot, update):
            domain, name, version, instance, role = j.atyourservice.parseKey(update.message.text)
            services = j.atyourservice.findServices(domain=domain, name=name, instance=instance, role=role)

            def execute(bot, update):
                action_name = update.message.text
                self.execute(bot, update, services, action_name)

            actions = set()
            for s in services:
                for action_name in s.recipe.actionmethods:
                    actions.add(action_name)

            def chunks(l, n):
                """Yield successive n-sized chunks from l."""
                for i in range(0, len(l), n):
                    yield l[i:i+n]

            actions = list(actions)
            actions.sort()
            keys = list(chunks(actions, 4))
            reply_markup = telegram.ReplyKeyboardMarkup(keys, resize_keyboard=True, one_time_keyboard=True)
            msg = 'Select the actions you want to execute'
            bot.sendMessage(chat_id=update.message.chat_id, text=msg, reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)
            self.callbacks[username] = execute

        self.callbacks[username] = select_action
        project_path = self._currentProjectPath(username)
        j.atyourservice.basepath = project_path
        services = list(j.atyourservice.services.keys())
        reply_markup = telegram.ReplyKeyboardMarkup([services], resize_keyboard=True, one_time_keyboard=True)
        msg = """
        Choose a service to execution action on or type a key to match multiple service.
        example :
        `@node` to match all service with role node
        `node!bot` to match the service with role node and instance name bot.
        """
        return bot.sendMessage(chat_id=update.message.chat_id, text=msg, reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)

    def delete_prompt(self, bot, update, project):
        username = update.message.from_user.username
        blueprints = j.sal.fs.listFilesInDir(self._currentBlueprintsPath(username))

        bluelist = []

        for bluepath in blueprints:
            blueprint = j.sal.fs.getBaseName(bluepath)
            bluelist.append(blueprint)

        if len(bluelist) == 0:
            return bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, this repository doesn't contains blueprint for now, upload me some of them !")

        def cb(bot, update):
            self.delete(bot, update, self._currentProject(username), [update.message.text])
        self.callbacks[username] = cb

        custom_keyboard = [bluelist]
        reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)
        return bot.sendMessage(chat_id=update.message.chat_id, text="Which blueprint do you want to delete ?", reply_markup=reply_markup)

    # Handler for robot
    def handler(self, bot, update, args):
        username = update.message.from_user.username

        self.bot.logger.debug('service management for: %s' % username)
        if not self.bot.project_mgmt._userCheck(bot, update):
            return

        if not self._currentProject(username):
            message = "Sorry, you are not working on a project currently, use `/project [name]` to create or select one"
            return bot.sendMessage(chat_id=update.message.chat_id, text=message, parse_mode="Markdown")

        # no arguments
        if len(args) == 0:
            self.choose_action(bot, update)
            return
            # return self.list(bot, update, self._currentProject(username))

        # list blueprints
        if args[0] == "list":
            return self.list(bot, update, self._currentProject(username))

        # # delete a blueprints
        # if (args[0] == "delete" or args[0] == "remove") and len(args) == 1:
        #     return self.delete_prompt(bot, update, self._currentProject(username))
        #
        # if (args[0] == "delete" or args[0] == "remove") and len(args) > 1:
        #     args.pop(0)
        #     return self.delete(bot, update, self._currentProject(username), args)
        #
        # if args[0] == "all":
        #     return self._blueprintGetAll(bot, update, self._currentProject(username))

        # retreive blueprint
        return self._blueprintGet(bot, update, args[0], self._currentProject(username))

    def document(self, bot, update):
        username = update.message.from_user.username
        doc = update.message.document
        item = bot.getFile(doc.file_id)
        local = '%s/%s' % (self._currentBlueprintsPath(username), doc.file_name)

        if not self._currentProject(username):
            message = "Sorry, you are not working on a project currently, use `/project [name]` to create a new one"
            return bot.sendMessage(chat_id=update.message.chat_id, text=message, parse_mode="Markdown")

        if j.sal.fs.exists(local):
            j.sal.fs.remove(local)

        self.bot.logger.debug("document: %s -> %s" % (item.file_path, local))
        j.sal.nettools.download(item.file_path, local)

        bot.sendMessage(chat_id=update.message.chat_id, text="File received: %s" % doc.file_name)
