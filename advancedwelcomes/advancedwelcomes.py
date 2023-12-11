from redbot.core import commands, Config, data_manager, checks
from redbot.core.bot import Red
import discord
import os
import sys
import asyncio
import aiohttp
import pathlib
import io
import random
from PIL import Image, ImageChops, ImageOps


class AdvancedWelcomes(commands.Cog):
    """Fully customizable welcome cog, with support for images"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 169234992, force_registration=True)

        default_guild = {
            "welcome_msg_channel": 802078699582521374,
            "toggle_msg": True,
            "toggle_img": False,
            "randomise_msg": False,
            "randomise_img": False,
            "def_welcome_msg": "Welcome, {USER}",
            "mandatory_msg_frag": "default mandatory message snippet",
            "message_pool": [],
            "img_avatar_cfgs": {},
        }

        self.config.register_guild(**default_guild)
        self.data_dir = data_manager.cog_data_path(cog_instance=self)
        self.img_dir = self.data_dir / "welcome_imgs"

        self.session = aiohttp.ClientSession()
        # a header to successfully download user avatars for use
        self.headers = {"User-agent": "Mozilla/5.0"}

        # create folder to hold welcome images
        try:
            os.mkdir(self.img_dir)
        except OSError as error:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        channel = discord.utils.get(
            guild.channels,
            id=await self.config.guild(guild).get_attr("welcome_msg_channel")(),
        )

        is_sending_msg = await self.config.guild(guild).get_attr("toggle_msg")()
        is_sending_img = await self.config.guild(guild).get_attr("toggle_img")()

        is_randomising_msg = await self.config.guild(guild).get_attr("randomise_msg")()
        is_randomising_img = await self.config.guild(guild).get_attr("randomise_img")()

        # if true, process welcome message and send
        welcome_msg = ""
        if is_randomising_msg:
            welcome_msg = str(await self.get_random_welcome_msg(member))
        elif is_sending_msg:
            welcome_msg = str(await self.get_welcome_msg(member))

        mandatory = await self.config.guild(guild).get_attr("mandatory_msg_frag")()
        welcome_msg = (
            welcome_msg.replace("{USER}", member.mention) + ". " + str(mandatory)
            if welcome_msg != ""
            else str(mandatory)
        )

        # if true, process welcome img and send
        if is_randomising_img:
            custom_img = await self.generate_random_welcome_img(member, guild)
        elif is_sending_img:
            custom_img = await self.generate_welcome_img(member, guild)

        send_msg = is_sending_msg or is_randomising_img
        send_img = is_sending_img or is_randomising_img

        # provides appropriate response according to settings
        if send_msg and send_img:
            await channel.send(
                welcome_msg, file=discord.File(custom_img, filename="output.png")
            )

        elif not send_msg and send_img:
            await channel.send(file=discord.File(custom_img, filename="output.png"))

        elif send_msg and not send_img:
            await channel.send(welcome_msg)

        elif not send_msg and not send_img:
            # do nothing
            pass

    ### Base command
    @commands.group(aliases=["cw"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def customwelcome(self, ctx: commands.Context):
        """Base command for customised welcome."""
        pass

    ### TOGGLE & UTLITY COMMANDS ###
    @customwelcome.group(aliases=["cfg", "config"])
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def welcome_configs(self, ctx: commands.Context):
        """Base command for configuring the customised welcome."""
        pass

    @welcome_configs.command(name="setch")
    @checks.mod_or_permissions(administrator=True)
    async def setwelcomech(self, ctx):
        """Call this in the channel where you want to display welcomes"""
        # Your code will go here
        await self.config.guild(ctx.author.guild).welcome_msg_channel.set(
            ctx.channel.id
        )
        await ctx.send("New welcome channel is: " + ctx.channel.mention)

    @welcome_configs.command(name="getstatus")
    @checks.mod_or_permissions(administrator=True)
    async def getwelcomestatus(self, ctx):
        """Call this in the channel where you want to display welcomes"""
        # Your code will go here
        channel = discord.utils.get(
            ctx.author.guild.channels,
            id=await self.config.guild(ctx.author.guild).get_attr(
                "welcome_msg_channel"
            )(),
        )
        try:
            await ctx.send("Current welcome channel is: " + channel.mention)
        except:
            await ctx.send(
                "There is no current channel set. Set one with the setch command."
            )
        await ctx.send(
            "Sending custom message: "
            + str(await self.config.guild(ctx.author.guild).get_attr("toggle_msg")())
        )
        await ctx.send(
            "Sending custom image: "
            + str(await self.config.guild(ctx.author.guild).get_attr("toggle_img")())
        )
        await ctx.send(
            "Randomising custom message: "
            + str(await self.config.guild(ctx.author.guild).get_attr("randomise_msg")())
        )
        await ctx.send(
            "Randomising custom image: "
            + str(await self.config.guild(ctx.author.guild).get_attr("randomise_img")())
        )

    @welcome_configs.command(name="togglemsg")
    @checks.mod_or_permissions(administrator=True)
    async def togglewelmsg(self, ctx):
        """Call this to toggle welcome message on and off"""
        value = await self.config.guild(ctx.author.guild).get_attr("toggle_msg")()

        # invert valuue
        value = not value

        # change value
        await self.config.guild(ctx.author.guild).toggle_msg.set(value)

        await ctx.send(
            "Sending custom message set to "
            + str(await self.config.guild(ctx.author.guild).get_attr("toggle_msg")())
        )

    @welcome_configs.command(name="toggleimg")
    @checks.mod_or_permissions(administrator=True)
    async def togglewelimg(self, ctx):
        """Call this to toggle welcome image on and off"""
        value = await self.config.guild(ctx.author.guild).get_attr("toggle_img")()

        # invert valuue
        value = not value

        # if setting to true, prevent toggle on if there is no image set
        if value and os.path.isfile(self.data_dir / "default.png") == False:
            await ctx.send("Set an image to use first please.")
            return

        # change value
        await self.config.guild(ctx.author.guild).toggle_img.set(value)

        await ctx.send(
            "Sending custom image set to "
            + str(await self.config.guild(ctx.author.guild).get_attr("toggle_img")())
        )

    @welcome_configs.command(name="togglerandommsg")
    @checks.mod_or_permissions(administrator=True)
    async def toggle_msg_randomiser(self, ctx):
        """Call this to toggle random welcome message on and off"""
        # await ctx.send("Not yet implemented!")
        # return

        value = await self.config.guild(ctx.author.guild).get_attr("randomise_msg")()

        # invert valuue
        value = not value

        # if setting to true and there arent any messages in the pool, prevent toggling to true
        if (
            value
            and len(
                await self.config.guild(ctx.author.guild).get_attr("message_pool")()
            )
            < 1
        ):
            await ctx.send(
                "There are currently no saved messages. Add at least one before turning the randomiser on"
            )
            return

        # change value
        await self.config.guild(ctx.author.guild).randomise_msg.set(value)

        await ctx.send(
            "randomising custom message set to "
            + str(await self.config.guild(ctx.author.guild).get_attr("randomise_msg")())
        )

    @welcome_configs.command(name="togglerandomimg")
    @checks.mod_or_permissions(administrator=True)
    async def toggle_img_randomiser(self, ctx):
        """Call this to toggle random welcome message on and off"""
        # await ctx.send("Not yet implemented!")
        # return
        value = await self.config.guild(ctx.author.guild).get_attr("randomise_img")()

        # invert valuue
        value = not value

        # if setting to true and there arent any images in the folder, prevent toggling to true
        if value and len(os.listdir(self.img_dir)) < 1:
            await ctx.send(
                "There are currently no images in the image_base folder. Add at least one before turning the randomiser on"
            )
            return

        # change value
        await self.config.guild(ctx.author.guild).randomise_img.set(value)

        await ctx.send(
            "randomising custom image set to "
            + str(await self.config.guild(ctx.author.guild).get_attr("randomise_img")())
        )

    @welcome_configs.command(name="currentgreet")
    @checks.mod_or_permissions(administrator=True)
    async def get_current_greeting(self, ctx):
        """fetches the current set image/text greetings & mandatory message snippet"""

        if await self.config.guild(ctx.author.guild).get_attr("randomise_msg")():
            await ctx.send(
                "Mandatory Message Fragment: "
                + str(
                    await self.config.guild(ctx.author.guild).get_attr(
                        "mandatory_msg_frag"
                    )()
                )
            )
            await ctx.send("Message being randomised from pool")
        elif await self.config.guild(ctx.author.guild).get_attr("toggle_msg")():
            await ctx.send(
                "Mandatory Message Fragment: "
                + str(
                    await self.config.guild(ctx.author.guild).get_attr(
                        "mandatory_msg_frag"
                    )()
                )
            )
            await ctx.send(
                "Current Message is: "
                + str(
                    await self.config.guild(ctx.author.guild).get_attr(
                        "def_welcome_msg"
                    )()
                )
            )
        else:
            await ctx.send("Welcome messages are disabled.")

        if await self.config.guild(ctx.author.guild).get_attr("randomise_img")():
            await ctx.send("Image being randomised from pool")
        elif await self.config.guild(ctx.author.guild).get_attr("toggle_img")():
            base_img_path = self.data_dir / "default.png"
            await ctx.send(
                "Current template image is: ", file=discord.File(base_img_path)
            )
        else:
            await ctx.send("Welcome images are disabled.")

    ### SET MESSAGE & PICTURE COMMANDS ###
    @customwelcome.group(aliases=["content"])
    @checks.mod_or_permissions(administrator=True)
    async def greetcontent(self, ctx: commands.Context):
        """Base command for configuring the image/text used for customised welcome."""
        pass

    @greetcontent.group(aliases=["set"])
    @checks.mod_or_permissions(administrator=True)
    async def setContent(self, ctx: commands.Context):
        """Base command for configuring the image/text used for customised welcome.This set of commands manages the non-random welcome settings."""
        pass

    @setContent.command(name="msg")
    @checks.mod_or_permissions(administrator=True)
    async def set_text(self, ctx, txt):
        """Sets the message to be sent when a user joins the server. This must be set before any welcome message is sent"""
        await self.config.guild(ctx.author.guild).def_welcome_msg.set(txt)
        new_welcome_message = "New welcome message is : {}"
        await ctx.send(
            new_welcome_message.format(
                await self.config.guild(ctx.author.guild).get_attr("def_welcome_msg")()
            )
        )

    @setContent.command(name="img")
    @checks.mod_or_permissions(administrator=True)
    async def set_image(self, ctx):
        """Sets the image to be sent when a user joins the server. This must be set before any welcome image is sent. Please only attach 1 image, make it fit into the template provided"""
        base_img_path = self.data_dir / "default.png"

        # user needs to specify where in the image should be the center of the joining user's avatar should be
        await ctx.send("reply to this message with the pixel x-coordinate")
        x_coord = -1
        try:
            x_coord = await self.bot.wait_for(
                "message",
                check=lambda message: message.author == ctx.author,
                timeout=30,
            )
        except asyncio.TimeoutError:
            await ctx.send("Adding image cancelled. Timed out. Try again")
            return

        try:
            x_coord = int(x_coord.content)
            assert x_coord >= 0
            await ctx.send(f"x:{x_coord}")
        except:
            await ctx.send(
                "Adding image cancelled. Please try again and enter a valid number."
            )
            return

        await ctx.send("reply to this message with the pixel y-coordinate")
        y_coord = -1
        try:
            y_coord = await self.bot.wait_for(
                "message",
                check=lambda message: message.author == ctx.author,
                timeout=30,
            )
        except asyncio.TimeoutError:
            await ctx.send("Adding image cancelled. Timed out. Try again")
            return

        try:
            y_coord = int(y_coord.content)
            assert y_coord >= 0
            await ctx.send(f"y:{y_coord}")
        except:
            await ctx.send(
                "Adding image cancelled. Please try again and enter a valid number."
            )
            return

        image = None
        if len(ctx.message.attachments) == 1:
            image = ctx.message.attachments[0]
            await image.save(base_img_path)
        else:
            await ctx.reply(
                "You need to attach exactly 1 image in the message that uses this command"
            )

        # ok now set the coordinate for where to put the avatar
        fetched_coord_dict = await self.config.guild(ctx.author.guild).get_attr(
            "img_avatar_cfgs"
        )()
        fetched_coord_dict.update({"default.png": [x_coord, y_coord]})
        await self.config.guild(ctx.author.guild).img_avatar_cfgs.set(
            fetched_coord_dict
        )

        # Performing necessary checks to ensure that this base can produce a good generated image
        temp = Image.open(base_img_path)
        temp_resize = temp.resize((1193, 671), 2)
        temp_resize.save(base_img_path, dpi=(72, 72))

        await image.save(base_img_path)

        # Performing necessary checks to ensure that this base can produce a good generated image
        temp = Image.open(base_img_path)
        temp_resize = temp.resize((1193, 671), 2)
        temp_resize.save(base_img_path, dpi=(72, 72))

        await ctx.reply("Welcome Image base set to: ", file=discord.File(base_img_path))

    @greetcontent.group(aliases=["add"])
    @checks.mod_or_permissions(administrator=True)
    async def addContent(self, ctx: commands.Context):
        """Base command for configuring the image/text used for customised welcome.This set of commands adds the content for random welcome settings."""
        pass

    @addContent.command(name="img")
    @checks.mod_or_permissions(administrator=True)
    async def add_img(self, ctx, name: str):
        """adds another image to the random image pool"""
        # determine potential file name
        file_name = f"{name}.png"
        img_path = self.img_dir / file_name

        if os.path.exists(img_path):
            await ctx.reply(
                "This name is already in use! For ease of management, please use another name."
            )
            return

        # user needs to specify where in the image should be the center of the joining user's avatar should be
        await ctx.send("reply to this message with the pixel x-coordinate")
        x_coord = -1
        try:
            x_coord = await self.bot.wait_for(
                "message",
                check=lambda message: message.author == ctx.author,
                timeout=30,
            )
        except asyncio.TimeoutError:
            await ctx.send("Adding image cancelled. Timed out. Try again")
            return

        try:
            x_coord = int(x_coord.content)
            assert x_coord >= 0
            await ctx.send(f"x:{x_coord}")
        except:
            await ctx.send(
                "Adding image cancelled. Please try again and enter a valid number."
            )
            return

        await ctx.send("reply to this message with the pixel y-coordinate")
        y_coord = -1
        try:
            y_coord = await self.bot.wait_for(
                "message",
                check=lambda message: message.author == ctx.author,
                timeout=30,
            )
        except asyncio.TimeoutError:
            await ctx.send("Adding image cancelled. Timed out. Try again")
            return

        try:
            y_coord = int(y_coord.content)
            assert y_coord >= 0
            await ctx.send(f"y:{y_coord}")
        except:
            await ctx.send(
                "Adding image cancelled. Please try again and enter a valid number."
            )
            return

        await ctx.send("reply to this message with the pixel radius")
        radius = -1
        try:
            radius = await self.bot.wait_for(
                "message",
                check=lambda message: message.author == ctx.author,
                timeout=30,
            )
        except asyncio.TimeoutError:
            await ctx.send("Adding image cancelled. Timed out. Try again")
            return

        try:
            radius = int(radius.content)
            assert radius >= 0
            await ctx.send(f"avatar radius:{radius}")
        except:
            await ctx.send(
                "Adding image cancelled. Please try again and enter a valid number."
            )
            return

        image = None
        if len(ctx.message.attachments) == 1:
            image = ctx.message.attachments[0]
            await image.save(img_path)
        else:
            await ctx.reply(
                "You need to attach exactly 1 image in the message that uses this command"
            )
            return

        # ok now set the coordinate for where to put the avatar
        fetched_coord_dict = await self.config.guild(ctx.author.guild).get_attr(
            "img_avatar_cfgs"
        )()
        fetched_coord_dict.update({file_name: [x_coord, y_coord, radius]})
        await self.config.guild(ctx.author.guild).img_avatar_cfgs.set(
            fetched_coord_dict
        )

        # Performing necessary checks to ensure that this base can produce a good generated image
        # temp = Image.open(img_path)
        # temp_resize = temp.resize((1193, 671), 2)
        # temp_resize.save(img_path, dpi=(72, 72))
        await ctx.reply("image added")

    @addContent.command(name="msg")
    @checks.mod_or_permissions(administrator=True)
    async def add_msg(self, ctx, message):
        """adds another message to the random message pool"""
        local_welcome_msgs = await self.config.guild(ctx.author.guild).get_attr(
            "message_pool"
        )()
        local_welcome_msgs.append(message)

        # updates database
        await self.config.guild(ctx.author.guild).message_pool.set(local_welcome_msgs)

        await ctx.reply(message + " added to random message pool")

    @greetcontent.group(aliases=["remove"])
    @checks.mod_or_permissions(administrator=True)
    async def removeContent(self, ctx: commands.Context):
        """Base command for configuring the image/text used for customised welcome.This set of commands removes saved content for random welcome settings."""
        pass

    @removeContent.command(name="img")
    async def remove_img(self, ctx, imgName: str):
        """Removes the specified image from the pool"""
        await self.ensureCurrentServerHasImgCache(ctx.channel)
        fileName = f"{imgName}.png"
        try:
            os.remove(self.img_dir / str(ctx.guild.id) / fileName)
        except:
            await ctx.reply("The named image doesn't exist")
            return

        # update coord info; remove
        coordInfo = await self.config.guild(ctx.guild).get_attr("img_avatar_cfgs")()
        coordInfo.pop(fileName)
        await self.config.guild(ctx.author.guild).img_avatar_cfgs.set(coordInfo)

        if len(os.listdir(self.img_dir / str(ctx.channel.guild.id))) == 0:
            await self.config.guild(ctx.author.guild).toggle_img.set(False)
            await ctx.reply("Last image deleted. Image randomiser turned off.")

        await ctx.reply("Image sucessfully removed")

    @removeContent.command(name="msg")
    @checks.mod_or_permissions(administrator=True)
    async def remove_msg(self, ctx, index):
        """removes a message to the random message pool"""
        try:
            index = int(index) - 1
        except:
            await ctx.send("Not a valid number")
            return
        local_welcome_msgs = await self.config.guild(ctx.author.guild).get_attr(
            "message_pool"
        )()
        message = local_welcome_msgs[index]

        # return if out of bounds
        if index < 0 or index > len(local_welcome_msgs):
            await ctx.reply("invalid index. Use listmsgs command to see indices.")
            return

        del local_welcome_msgs[index]

        # updates database
        await self.config.guild(ctx.author.guild).message_pool.set(local_welcome_msgs)

        await ctx.reply(
            f"'{message}'" + f" at index {index} removed from random message pool"
        )

    @greetcontent.group(aliases=["view"])
    @checks.mod_or_permissions(administrator=True)
    async def viewContent(self, ctx: commands.Context):
        """Base command for configuring the image/text used for customised welcome.This set of commands removes saved content for random welcome settings."""
        pass

    @viewContent.command(name="template")
    async def get_template(self, ctx):
        """responds to command with the template for the welcome image so users can create their own easier"""
        await ctx.reply(
            "Here is the template file! The image is 72dpi, 1193 x 671, but you can use any resolution",
            file=discord.File(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "welcome_template.png"
                )
            ),
        )

    @viewContent.command(name="listimgs")
    async def listImg(self, ctx):
        """Display a list of all the images in this server's image cache"""
        await self.ensureCurrentServerHasImgCache(ctx.channel)
        listOfImages = "\n".join(
            imagePath.stem
            for imagePath in pathlib.Path(
                self.img_dir / str(ctx.channel.guild.id)
            ).iterdir()
        )
        if len(listOfImages) == 0:
            await ctx.reply("No images added yet.")
            return
        await ctx.reply(listOfImages)

    @viewContent.command(name="listmsgs")
    async def listMsgs(self, ctx):
        """Display a list of all the messages in this server's random message cache"""
        local_welcome_msgs = await self.config.guild(ctx.author.guild).get_attr(
            "message_pool"
        )()
        index = 0
        listOfMessages = ""
        for i in local_welcome_msgs:
            listOfMessages = listOfMessages + f"\n{index + 1}. " + i
            index += 1

        if len(listOfMessages) == 0:
            await ctx.reply("No messages added yet.")
            return
        await ctx.reply(listOfMessages)

    @greetcontent.command(name="setmandatory")
    @checks.mod_or_permissions(administrator=True)
    async def set_mandatory_text(self, ctx, txt):
        """Sets the mandatory message snippet to be sent with the message thats sent when a user joins the server"""
        await self.config.guild(ctx.author.guild).mandatory_msg_frag.set(txt)
        new_welcome_message = "New mandatory message snippet is : {}"
        await ctx.send(
            new_welcome_message.format(
                await self.config.guild(ctx.author.guild).get_attr(
                    "mandatory_msg_frag"
                )()
            )
        )

    ### HELPER FUNCTIONS
    ### CUSTOM WELCOME PICTURE GENERATION ###
    async def generate_welcome_img(self, user, guild):
        """creates an image for the specific player using their avatar and the set base image, then returns it"""
        base = Image.open(self.data_dir / "default.png")
        mask = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "MASK.png")
        )
        border_overlay = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "BORDER.png")
        )
        border_overlay_mask = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "BORDER_mask.png")
        )
        # get avatar from User
        avatar: bytes

        # try:
        #     async with self.session.get(str(user.avatar_url), headers = self.headers) as webp:
        #         avatar = await webp.read()
        # except aiohttp.ClientResponseError:
        #     pass

        avatar = await user.avatar.read()

        with Image.open(io.BytesIO(avatar)) as retrieved_avatar:
            if not retrieved_avatar:
                return
            else:
                # get coords
                coordInfo = await self.config.guild(guild).get_attr("img_avatar_cfgs")()
                coords = coordInfo.get("default.png")
                # base = base.resize((1193, 671), 2)
                retrieved_avatar = retrieved_avatar.resize((coords[2], coords[2]), 1)
                base.paste(border_overlay, (coords[0], coords[1]), border_overlay_mask)
                base.paste(retrieved_avatar, (coords[0], coords[1]), mask)
                generated = io.BytesIO()
                base.save(generated, format="png")
                generated.seek(0)
                return generated

    async def generate_random_welcome_img(self, user, guild):
        """creates an image for the specific player using their avatar and an image from the random image pool, then returns it"""
        chosen = random.choice(os.listdir(self.img_dir))
        base = Image.open(self.img_dir / chosen)
        mask = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "MASK.png")
        )
        border_overlay = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "BORDER.png")
        )
        border_overlay_mask = Image.open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "BORDER_mask.png")
        )
        # get avatar from User
        avatar: bytes

        # try:
        #     async with self.session.get(str(user.avatar_url), headers = self.headers) as webp:
        #         avatar = await webp.read()
        # except aiohttp.ClientResponseError:
        #     pass

        avatar = await user.avatar.read()

        with Image.open(io.BytesIO(avatar)) as retrieved_avatar:
            if not retrieved_avatar:
                return
            else:
                # get coords
                coordInfo = await self.config.guild(guild).get_attr("img_avatar_cfgs")()
                coords = coordInfo.get(chosen)
                # base = base.resize((1193, 671), 2) default (434,0)
                retrieved_avatar = retrieved_avatar.resize((coords[2], coords[2]), 1)
                base.paste(
                    border_overlay,
                    (coords[0], coords[1]),
                    border_overlay_mask,
                )
                base.paste(retrieved_avatar, (coords[0], coords[1]), mask)
                generated = io.BytesIO()
                base.save(generated, format="png")
                generated.seek(0)
                return generated

    ### CUSTOM WELCOME MESSAGE GENERATION ###
    async def get_welcome_msg(self, author):
        msg = await self.config.guild(author.guild).get_attr("def_welcome_msg")()
        return msg

    async def get_random_welcome_msg(self, author):
        local_welcome_msgs = await self.config.guild(author.guild).get_attr(
            "message_pool"
        )()
        return random.choice(local_welcome_msgs)

    async def ensureCurrentServerHasImgCache(self, channel: discord.channel):
        """
        Check if there is a folder in the image cache for the associated server. If one doesn't exist, creates it.
        """
        idStr = str(channel.guild.id)
        fp = self.img_dir / idStr
        if os.path.exists(fp):
            return

        try:
            os.makedirs(fp, exist_ok=True)
            await channel.send(
                "No image cache folder found for this server! Created one"
            )

        except OSError as info:
            await channel.send("Something went wrong...")
