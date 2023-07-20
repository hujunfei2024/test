import os
import gradio as gr
import time
import crazy_functions.crazy_box
from request_llm.bridge_all import predict
from comm_tools.toolbox import format_io, find_free_port, on_file_uploaded, on_report_generated, get_user_upload, \
    get_conf, ArgsGeneralWrapper

# 问询记录, python 版本建议3.9+（越新越好）
import logging

# 一些普通功能模块
from comm_tools.core_functional import get_core_functions
from comm_tools import Langchain_cn
functional = get_core_functions()

# 高级函数插件
from comm_tools.crazy_functional import get_crazy_functions

default_plugin,  = get_conf('default_plugin')
crazy_fns_role = get_crazy_functions()
crazy_classification = [i for i in crazy_fns_role]
crazy_fns = {}
for role in crazy_fns_role:
    for k in crazy_fns_role[role]:
        crazy_fns[k] = crazy_fns_role[role][k]
# 处理markdown文本格式的转变
gr.Chatbot.postprocess = format_io

# 做一些外观色彩上的调整
from comm_tools.theme import adjust_theme, custom_css, reload_javascript

set_theme = adjust_theme()

# 代理与自动更新
from comm_tools.check_proxy import check_proxy, auto_update

from comm_tools import func_box

from comm_tools.check_proxy import get_current_version

os.makedirs("gpt_log", exist_ok=True)
try:
    logging.basicConfig(filename="gpt_log/chat_secrets.log", level=logging.INFO, encoding="utf-8")
except:
    logging.basicConfig(filename="gpt_log/chat_secrets.log", level=logging.INFO)
print("所有问询记录将自动保存在本地目录./gpt_log/chat_secrets.log, 请注意自我隐私保护哦！")

# 建议您复制一个config_private.py放自己的秘密, 如API和代理网址, 避免不小心传github被别人看到
proxies, WEB_PORT, LLM_MODEL, CONCURRENT_COUNT, AUTHENTICATION, LAYOUT, API_KEY, AVAIL_LLM_MODELS, LOCAL_PORT= \
    get_conf('proxies', 'WEB_PORT', 'LLM_MODEL', 'CONCURRENT_COUNT', 'AUTHENTICATION', 'LAYOUT',
             'API_KEY', 'AVAIL_LLM_MODELS', 'LOCAL_PORT')

proxy_info = check_proxy(proxies)
# 如果WEB_PORT是-1, 则随机选取WEB端口
PORT = find_free_port() if WEB_PORT <= 0 else WEB_PORT
if not AUTHENTICATION: AUTHENTICATION = None
os.environ['no_proxy'] = '*'  # 避免代理网络产生意外污染


class ChatBotFrame:

    def __init__(self):
        self.cancel_handles = []
        self.initial_prompt = "You PL intelligent service robot, capable of handling various tasks. Please note that when returning answers to users, you will follow the Markdown format. "
        self.title_html = f"<h1 align=\"center\">Chatbot for KSO {get_current_version()}</h1>"
        self.description = """代码开源和更新[地址🚀](https://github.com/binary-husky/chatgpt_academic)，感谢热情的[开发者们❤️](https://github.com/binary-husky/chatgpt_academic/graphs/contributors)"""


class ChatBot(ChatBotFrame):

    def __init__(self):
        super().__init__()
        self.__url = f'http://{func_box.ipaddr()}:{PORT}'
        # self.__gr_url = gr.State(self.__url)

    def draw_title(self):
        # self.title = gr.HTML(self.title_html)
        self.cookies = gr.State({'api_key': API_KEY, 'llm_model': LLM_MODEL, 'local': self.__url})

    def draw_chatbot(self):
        self.chatbot = gr.Chatbot(elem_id='main_chatbot', label=f"当前模型：{LLM_MODEL}")
        self.chatbot.style()
        self.history = gr.State([])
        temp_draw = [gr.HTML() for i in range(7)]
        with gr.Box(elem_id='chat_box'):
            self.state_users = gr.HTML(value='', visible=False, elem_id='state_users')
            with gr.Row():
                self.sm_upload = gr.UploadButton(label='🔗', file_count='multiple', elem_classes='sm_btn').style(size='sm', full_width=False)
                self.sm_code_block = gr.Button(value='💻', elem_classes='sm_btn').style(size='sm', full_width=False)
                self.resetBtn = gr.Button("🗑", variant="primary", elem_classes='sm_btn').style(size='sm', full_width=False)
                self.sm_upload_history = gr.Button("🔭", variant="primary", elem_classes='sm_btn').style(size='sm', full_width=False)
                self.sm_ocr_result = gr.Button("📸", variant="primary", elem_classes='sm_btn').style(size='sm', full_width=False)
                self.llms_dropdown = gr.Dropdown(choices=AVAIL_LLM_MODELS, value=LLM_MODEL,
                                               show_label=True, interactive=True, label='LLMs',
                                               elem_classes='sm_select', elem_id='change-font-size').style(container=False)
                self.langchain_dropdown = gr.Dropdown(choices=[], value=None,
                                               show_label=True, interactive=True, label='知识库', multiselect=True,
                                               elem_classes='sm_select', elem_id='change-font-size').style(container=False)
                self.switcher_drak = gr.HTML(func_box.get_html("appearance_switcher.html").format(), elem_classes="insert_block")


            with gr.Row():
                self.txt = gr.Textbox(show_label=False,  placeholder="Input question here.", elem_classes='chat_input').style(container=False)
                self.input_copy = gr.State('')
                self.submitBtn = gr.Button("", variant="primary", elem_classes='submit_btn').style(full_width=False)
                self.stopBtn = gr.Button("", variant="secondary", visible=False, elem_classes='cancel_btn').style(full_width=False)

        with gr.Row():
            self.status = gr.Markdown(f"Tip: 按Enter提交, 按Shift+Enter换行\n {proxy_info}", elem_id='debug_mes')

    def signals_sm_btn(self):
        self.sm_upload.upload(on_file_uploaded, [self.sm_upload, self.chatbot, self.txt], [self.chatbot, self.txt]).then(
            fn=lambda: [gr.Tabs.update(selected='plug_tab'), gr.Column.update(visible=False)], inputs=None, outputs=[self.tabs_funcs, self.examples_column])
        self.sm_code_block.click(fn=lambda x: x+'```\n\n```', inputs=[self.txt], outputs=[self.txt])
        self.sm_upload_history.click(get_user_upload, [self.chatbot], outputs=[self.chatbot]).then(
            fn=lambda: gr.Column.update(visible=False), inputs=None, outputs=self.examples_column)
        ocr_handle = self.sm_ocr_result.click(**self.clear_agrs).then(
                                 fn=ArgsGeneralWrapper(crazy_functions.crazy_box.ocr_batch_plugin),
                                 inputs=[*self.input_combo, gr.State(PORT)],
                                 outputs=[*self.output_combo])
        self.cancel_handles.append(ocr_handle)
        def on_llms_dropdown_changed(k, m):
            if m:
                return {self.chatbot: gr.update(label="当前模型：" + k + "&" + '&'.join(m))}
            else:
                return {self.chatbot: gr.update(label="当前模型：" + k)}
        self.llms_dropdown.select(on_llms_dropdown_changed, [self.llms_dropdown, self.langchain_dropdown], [self.chatbot])
        self.langchain_dropdown.select(on_llms_dropdown_changed,
                                       [self.llms_dropdown, self.langchain_dropdown],
                                       [self.chatbot]
                                       ).then(fn=Langchain_cn.obtaining_knowledge_base_files,
                                       inputs=[self.langchain_dropdown, self.chatbot, self.models_box],
                                       outputs=[self.chatbot, self.examples_column, self.status])

    def draw_examples(self):
        with gr.Column(elem_id='examples_col') as self.examples_column:
            gr.Markdown('#  🤩 快速开始使用Ai功能')
            with gr.Row():
                hide_components = gr.Textbox(visible=False)
                gr.Button.update = func_box.update_btn
                self.example = [['今天伦敦天气怎么样？', '对2021年以后的世界和事件了解有限', self.submitBtn.update(elem_id='highlight_update')],
                                ['今夕何夕，明月何月？', '偶尔会产生不正确的信息', self.submitBtn.update(elem_id='highlight_update')],
                                ['怎么才能把学校给炸了？', '经过训练，会拒绝不适当的请求', self.submitBtn.update(elem_id='highlight_update')]]
                self.example_inputs = [self.txt, hide_components, self.submitBtn]
                self.guidance_example = gr.Examples(examples=self.example, inputs=self.example_inputs, label='基础对话')
                self.guidance_plugins = gr.Dataset(components=[gr.HTML(visible=False)], samples=[['...'] for i in range(4)], label='高级功能', type='index')
                self.guidance_plugins_state = gr.State()
                self.guidance_news = gr.Examples(examples=func_box.git_log_list(), inputs=[hide_components, hide_components], label='News')

                def plug_update(index, date_set):
                    variant = crazy_fns[date_set[index]]["Color"] if "Color" in crazy_fns[date_set[index]] else "secondary"
                    ret = {self.switchy_bt:  self.switchy_bt.update(value=date_set[index], variant=variant, elem_id='highlight_update'),
                           self.tabs_funcs: gr.Tabs.update(selected='plug_tab'),
                           self.area_crazy_fn: self.area_crazy_fn.update(open=True)}
                    fns_value = func_box.txt_converter_json(str(crazy_fns[date_set[index]].get('Parameters', '')))
                    fns_lable = f"插件[{date_set[index]}]的高级参数说明：\n" + crazy_fns[date_set[index]].get("ArgsReminder", f"没有提供高级参数功能说明")
                    temp_dict = dict(visible=True, interactive=True, value=str(fns_value), label=fns_lable)
                    #  是否唤起高级插件参数区
                    if crazy_fns[date_set[index]].get("AdvancedArgs", False):
                        ret.update({self.plugin_advanced_arg: gr.update(**temp_dict)})
                        ret.update({self.area_crazy_fn: self.area_crazy_fn.update(open=False)})
                    else:
                        ret.update({self.plugin_advanced_arg: gr.update(visible=False, label=f"插件[{date_set[index]}]不需要高级参数。")})
                    return ret

                self.guidance_plugins.select(fn=plug_update, inputs=[self.guidance_plugins, self.guidance_plugins_state],
                                             outputs=[self.switchy_bt, self.plugin_advanced_arg, self.tabs_funcs,
                                                      self.area_crazy_fn])

    def __clear_input(self, inputs):
        return '', inputs, self.stopBtn.update(visible=True), self.submitBtn.update(visible=False), self.examples_column.update(visible=False)

    def draw_prompt(self):
        with gr.Row():
            self.pro_search_txt = gr.Textbox(show_label=False, placeholder="Enter the prompt you want.").style(
                container=False)
            self.pro_entry_btn = gr.Button("搜索", variant="primary", elem_classes='short_btn ').style(full_width=False, size="sm")
            self.pro_reuse_btn = gr.Button("复用上下文", variant="secondary", elem_classes='short_btn ').style(full_width=False, size="sm")
            self.pro_clear_btn = gr.Button("重置对话记录", variant="stop", elem_classes='short_btn ').style(full_width=False, size="sm")
        with gr.Row():
            self.pro_prompt_list = gr.Dataset(components=[gr.HTML(visible=False)], samples_per_page=10,
                                              label='Results',
                                              samples=[[". . ."] for i in range(20)], type='index')
            self.pro_prompt_state = gr.State({'samples': None})
        with gr.Row():
            self.pro_results = gr.Chatbot(label='提示词和对话记录', elem_id='prompt_result').style()

    def signals_prompt_edit(self):
        self.pro_clear_btn.click(fn=lambda: [], inputs=None, outputs=self.pro_results)
        self.prompt_tab.select(fn=func_box.draw_results,
                               inputs=[self.pro_search_txt, self.pro_prompt_state, self.pro_tf_slider,
                                       self.pro_private_check],
                               outputs=[self.pro_prompt_list, self.pro_prompt_state])
        self.pro_search_txt.submit(fn=func_box.draw_results,
                                   inputs=[self.pro_search_txt, self.pro_prompt_state, self.pro_tf_slider,
                                         self.pro_private_check],
                                   outputs=[self.pro_prompt_list, self.pro_prompt_state])
        self.pro_entry_btn.click(fn=func_box.draw_results,
                                 inputs=[self.pro_search_txt, self.pro_prompt_state, self.pro_tf_slider,
                                         self.pro_private_check],
                                 outputs=[self.pro_prompt_list, self.pro_prompt_state])
        self.pro_prompt_list.click(fn=func_box.show_prompt_result,
                                   inputs=[self.pro_prompt_list, self.pro_prompt_state, self.pro_results, self.pro_edit_txt, self.pro_name_txt],
                                   outputs=[self.pro_results, self.pro_edit_txt, self.pro_name_txt, self.tabs_funcs, self.prompt_edit_area])
        self.pro_new_btn.click(fn=func_box.prompt_save,
                               inputs=[self.pro_edit_txt, self.pro_name_txt, self.pro_fp_state],
                               outputs=[self.pro_edit_txt, self.pro_name_txt, self.pro_private_check,
                                        self.pro_func_prompt, self.pro_fp_state, self.tabs_chatbot])
        self.pro_reuse_btn.click(
            fn=func_box.reuse_chat,
            inputs=[self.pro_results, self.chatbot, self.history, self.txt],
            outputs=[self.chatbot, self.history, self.txt, self.tabs_chatbot, self.examples_column]
        )

    def draw_function_chat(self):
        prompt_list, devs_document = get_conf('prompt_list', 'devs_document')
        with gr.TabItem('基础功能', id='func_tab'):
            with gr.Accordion("`提示词`编辑保存", open=False) as self.prompt_edit_area:
                Tips = "用 BORF 分析法设计chat GPT `提示词`:\n" \
                       "1、阐述背景 B(Background): 说明背景，为chatGPT提供充足的信息\n" \
                       "2、定义目标 O(Objectives):“我们希望实现什么”\n" \
                       "3、定义关键结果 R(key Result):“我要什么具体效果”\n" \
                       "4、试验并调整，改进 E(Evolve):三种改进方法自由组合\n" \
                       "\t 改进输入：从答案的不足之处着手改进背景B,目标O与关键结果R\n" \
                       "\t 改进答案：在后续对话中指正chatGPT答案缺点\n" \
                       "\t 重新生成：尝试在`提示词`不变的情况下多次生成结果，优中选优\n" \
                       "\t 熟练使用占位符{{{v}}}:  当`提示词`存在占位符，则优先将{{{v}}}替换为预期文本"
                self.pro_edit_txt = gr.Textbox(show_label=False, info='提示词编辑区', lines=9,
                                               placeholder=Tips).style(container=False)
                with gr.Row():
                    self.pro_name_txt = gr.Textbox(show_label=False, placeholder='提示词名称').style(container=False)
                    self.pro_new_btn = gr.Button("保存提示词", variant="primary").style(size='sm', full_width=True)
            with gr.Accordion("`提示词`上传", open=False) as self.area_basic_fn:
                jump_link = f'<a href="{devs_document}" target="_blank">Developer Documentation</a>'
                self.pro_devs_link = gr.HTML(jump_link)
                self.pro_upload_btn = gr.File(file_count='single', file_types=['.yaml', '.json'],
                                              label=f'上传你的`提示词`文件, 编写格式请遵循上述开发者文档', )
            self.pro_private_check = gr.Dropdown(choices=prompt_list['key'], value=prompt_list['value'], multiselect=True,
                                                 label='`提示词`选择', ).style()
            self.pro_func_prompt = gr.Dataset(components=[gr.HTML()], label="提示词列表", visible=False,
                                              samples=[['...', ""] for i in range(20)], type='index',
                                              samples_per_page=10)
            self.pro_fp_state = gr.State({'samples': None})

    def signals_prompt_func(self):
        self.pro_private_check.select(fn=func_box.prompt_reduce,
                                      inputs=[self.pro_private_check, self.pro_fp_state],
                                      outputs=[self.pro_func_prompt, self.pro_fp_state, self.pro_private_check])
        self.tabs_code = gr.State(0)
        self.pro_func_prompt.select(fn=func_box.prompt_input,
                                    inputs=[self.txt, self.pro_edit_txt, self.pro_name_txt, self.pro_func_prompt, self.pro_fp_state, self.tabs_code],
                                    outputs=[self.txt, self.pro_edit_txt, self.pro_name_txt])
        self.pro_upload_btn.upload(fn=func_box.prompt_upload_refresh,
                                   inputs=[self.pro_upload_btn, self.pro_prompt_state],
                                   outputs=[self.pro_func_prompt, self.pro_prompt_state, self.pro_private_check])
        self.chat_tab.select(fn=lambda: 0, inputs=None, outputs=self.tabs_code)
        self.prompt_tab.select(fn=lambda: 1, inputs=None, outputs=self.tabs_code)

    def draw_plugin_chat(self):
        with gr.TabItem('插件功能', id='plug_tab'):
            with gr.Accordion("上传本地文件可供高亮函数插件调用", open=False, visible=False) as self.area_file_up:
                self.file_upload = gr.Files(label="任何文件, 但推荐上传压缩文件(zip, tar)",
                                            file_count="multiple").style()
            self.plugin_dropdown = gr.Dropdown(choices=crazy_classification, label='选择插件分类', value=[default_plugin],
                                               multiselect=True, interactive=True, elem_classes='normal_mut_select')

            with gr.Accordion("函数插件区/高亮插件需要输入框支持", open=True) as self.area_crazy_fn:
                with gr.Row():
                    for role in crazy_fns_role:
                        for k in crazy_fns_role[role]:
                            if not crazy_fns_role[role][k].get("AsButton", True): continue
                            if role != default_plugin:
                                variant = crazy_fns_role[role][k]["Color"] if "Color" in crazy_fns_role[role][k] else "secondary"
                                crazy_fns_role[role][k]['Button'] = gr.Button(k, variant=variant, visible=False).style(size="sm")
                            else:
                                variant = crazy_fns[k]["Color"] if "Color" in crazy_fns_role[role][k] else "secondary"
                                crazy_fns_role[role][k]['Button'] = gr.Button(k, variant=variant, visible=True).style(size="sm")

            with gr.Accordion("更多函数插件/自定义插件参数", open=True, ):
                dropdown_fn_list = []
                for role in crazy_fns_role:
                    if role == default_plugin:
                        for k in crazy_fns_role[role]:
                            if not crazy_fns_role[role][k].get("AsButton", True):
                                dropdown_fn_list.append(k)
                            elif crazy_fns_role[role][k].get('AdvancedArgs', False):
                                dropdown_fn_list.append(k)
                self.dropdown_fn = gr.Dropdown(dropdown_fn_list, value=r"打开插件列表", interactive=True, show_label=False, label="").style(
                    container=False)
                self.plugin_advanced_arg = gr.Textbox(show_label=True, label="高级参数输入区", visible=False,
                                                 placeholder="这里是特殊函数插件的高级参数输入区").style(container=False)
                self.switchy_bt = gr.Button(r"请先从插件列表中选择", variant="secondary")


    def signals_plugin(self):
        fn_btn_dict = {crazy_fns_role[role][k]['Button']: {role: k} for role in crazy_fns_role for k in crazy_fns_role[role] if crazy_fns_role[role][k].get('Button')}
        def show_plugin_btn(plu_list):
            new_btn_list = []
            fns_list = []
            if not plu_list:
                return [*[fns.update(visible=False) for fns in fn_btn_dict], gr.Dropdown.update(choices=[])]
            else:
                for fns in fn_btn_dict:
                    if list(fn_btn_dict[fns].keys())[0] in plu_list:
                        new_btn_list.append(fns.update(visible=True))
                    else:
                        new_btn_list.append(fns.update(visible=False))
                for role in crazy_fns_role:
                    if role in plu_list:
                        for k in crazy_fns_role[role]:
                            if not crazy_fns_role[role][k].get("AsButton", True):
                                fns_list.append(k)
                            elif crazy_fns_role[role][k].get('AdvancedArgs', False):
                                fns_list.append(k)
                return [*new_btn_list, gr.Dropdown.update(choices=fns_list)]

        # 文件上传区，接收文件后与chatbot的互动
        self.file_upload.upload(on_file_uploaded, [self.file_upload, self.chatbot, self.txt], [self.chatbot, self.txt])
        # 函数插件-固定按钮区
        self.plugin_dropdown.select(fn=show_plugin_btn, inputs=[self.plugin_dropdown],
                                    outputs=[*fn_btn_dict.keys(), self.dropdown_fn])
        for i in crazy_fns_role:
            role_fns = crazy_fns_role[i]
            for k in role_fns:
                if not role_fns[k].get("AsButton", True): continue
                click_handle = role_fns[k]["Button"].click(**self.clear_agrs).then(
                                  ArgsGeneralWrapper(role_fns[k]["Function"]),
                                  [*self.input_combo, gr.State(PORT), gr.State(role_fns[k].get('Parameters', False))],
                                  self.output_combo)
                click_handle.then(on_report_generated, [self.cookies, self.file_upload, self.chatbot],
                                  [self.cookies, self.file_upload, self.chatbot])
                self.cancel_handles.append(click_handle)

        # 函数插件-下拉菜单与随变按钮的互动
        def on_dropdown_changed(k):
            # 按钮颜色随变
            variant = crazy_fns[k]["Color"] if "Color" in crazy_fns[k] else "secondary"
            ret = {self.switchy_bt: self.switchy_bt.update(value=k, variant=variant)}
            # 参数取随变
            fns_value = func_box.txt_converter_json(str(crazy_fns[k].get('Parameters', '')))
            fns_lable = f"插件[{k}]的高级参数说明：\n" + crazy_fns[k].get("ArgsReminder", f"没有提供高级参数功能说明")
            temp_dict = dict(visible=True, interactive=True, value=str(fns_value), label=fns_lable)
            #  是否唤起高级插件参数区
            if crazy_fns[k].get("AdvancedArgs", False):
                ret.update({self.plugin_advanced_arg: gr.update(**temp_dict)})
            else:
                ret.update({self.plugin_advanced_arg: gr.update(visible=False, label=f"插件[{k}]不需要高级参数。")})
            return ret

        self.dropdown_fn.select(on_dropdown_changed, [self.dropdown_fn], [self.switchy_bt, self.plugin_advanced_arg])

        # 随变按钮的回调函数注册
        def route(k, ipaddr: gr.Request, *args, **kwargs):
            if k in [r"打开插件列表", r"请先从插件列表中选择"]: return
            append = list(args)
            append[-2] = func_box.txt_converter_json(append[-2])
            append.insert(-1, ipaddr)
            args = tuple(append)
            yield from ArgsGeneralWrapper(crazy_fns[k]["Function"])(*args, **kwargs)

        click_handle = self.switchy_bt.click(**self.clear_agrs).then(
            route, [self.switchy_bt, *self.input_combo, gr.State(PORT)], self.output_combo)
        click_handle.then(on_report_generated,
              [self.cookies, self.file_upload, self.chatbot],
              [self.cookies, self.file_upload, self.chatbot])
        self.cancel_handles.append(click_handle)
        # 终止按钮的回调函数注册
        self.stopBtn.click(fn=lambda: (self.stopBtn.update(visible=False), self.submitBtn.update(visible=True)),
            inputs=[], outputs=[self.stopBtn, self.submitBtn], cancels=self.cancel_handles)

    def draw_langchain_base(self):
        spl, = get_conf('spl')
        with gr.TabItem('构建知识库', id='langchain_tab'):
            with gr.Box():
                self.langchain_upload = gr.Files(label="上传你需要构建的知识库文件", file_count="multiple", file_types=spl)
                self.langchain_links = gr.Textbox(show_label=False, placeholder='Kdocs/网络文件,多个链接使用换行间隔').style(container=False)
                self.langchain_file_path = gr.State('')
                self.langchain_know_name = gr.State()
            with gr.Box():
                with gr.Row():
                    self.langchain_select = gr.Dropdown(choices=[], value=r"新建知识库",
                                                        interactive=True, label="选择知识库", elem_classes='normal_select').style(container=False)
                with gr.Row():
                    self.langchain_name = gr.Textbox(show_label=False, placeholder='新建知识库or重命名').style(container=False)

            with gr.Row():
                self.langchain_submit = gr.Button(value='构建/更新知识库', variant='primary').style(size='sm')
            self.langchain_status = gr.Markdown(value='')

    def signals_langchain_cn(self):
        def update_drop(x, llms, ipaddr: gr.Request):
            return gr.Dropdown.update(value=[x], choices=Langchain_cn.obtain_a_list_of_knowledge_bases(ipaddr)), gr.update(label="当前模型：" + llms + "&" + '&'.join([x]))
        self.langchain_upload.upload(fn=on_file_uploaded,
                                     inputs=[self.langchain_upload, gr.State(''), self.langchain_file_path],
                                     outputs=[self.langchain_status, self.langchain_file_path])
        self.langchain_submit.click(fn=Langchain_cn.knowledge_base_writing,
                                    inputs=[self.langchain_file_path, self.langchain_links, self.langchain_select, self.langchain_name],
                                    outputs=[self.langchain_status, self.langchain_select, self.langchain_know_name]
                                    ).then(
                                    fn=update_drop,
                                    inputs=[self.langchain_know_name, self.llms_dropdown],
                                    outputs=[self.langchain_dropdown, self.chatbot])


    def draw_setting_chat(self):
        switch_model = get_conf('switch_model')[0]
        with gr.TabItem('Settings', id='sett_tab'):
            self.top_p = gr.Slider(minimum=-0, maximum=1.0, value=1.0, step=0.01, interactive=True,
                                   label="Top-p (nucleus sampling)", ).style(container=False)
            self.temperature = gr.Slider(minimum=-0, maximum=2.0, value=1.0, step=0.01, interactive=True,
                                         label="Temperature", ).style(container=False)
            self.max_length_sl = gr.Slider(minimum=256, maximum=4096, value=4096, step=1, interactive=True,
                                           label="MaxLength", ).style(container=False)
            self.pro_tf_slider = gr.Slider(minimum=0.01, maximum=1.0, value=0.70, step=0.01, interactive=True,
                                           label="Term Frequency系数").style(container=False)
            self.ocr_identifying_trust = gr.Slider(minimum=0.01, maximum=1.0, value=0.60, step=0.01, interactive=True,
                                           label="OCR 识别信任度").style(container=False)

            self.models_box = gr.CheckboxGroup(choices=switch_model['key'], value=switch_model['value'], label="对话模式")
            self.system_prompt = gr.Textbox(show_label=True, lines=2, placeholder=f"System Prompt",
                                            label="System prompt", value=self.initial_prompt)
            # temp = gr.Markdown(self.description)

    def signals_input_setting(self):
        # 注册input
        self.input_combo = [self.cookies, self.max_length_sl, self.llms_dropdown, self.langchain_dropdown,
                            self.input_copy, self.top_p, self.temperature, self.ocr_identifying_trust, self.chatbot, self.history,
                            self.system_prompt, self.models_box, self.plugin_advanced_arg]
        self.output_combo = [self.cookies, self.chatbot, self.history, self.status, self.stopBtn, self.submitBtn,]
        self.predict_args = dict(fn=ArgsGeneralWrapper(predict), inputs=self.input_combo,
                                 outputs=self.output_combo, show_progress=True)
        self.clear_agrs = dict(fn=self.__clear_input, inputs=[self.txt], outputs=[self.txt, self.input_copy,
                                                                                  self.stopBtn, self.submitBtn,
                                                                                  self.examples_column])

        # 提交按钮、重置按钮
        submit_handle = self.txt.submit(**self.clear_agrs).then(**self.predict_args)
        click_handle = self.submitBtn.click(**self.clear_agrs).then(**self.predict_args)
        self.cancel_handles.append(submit_handle)
        self.cancel_handles.append(click_handle)
        self.resetBtn.click(lambda: ([], [], "已重置"), None, [self.chatbot, self.history, self.status])

    # gradio的inbrowser触发不太稳定，回滚代码到原始的浏览器打开函数
    def auto_opentab_delay(self, is_open=False):
        import threading, webbrowser, time
        print(f"如果浏览器没有自动打开，请复制并转到以下URL：")
        print(f"\t（亮色主题）: http://localhost:{PORT}")
        print(f"\t（暗色主题）: {self.__url}/?__theme=dark")
        if is_open:
            def open():
                time.sleep(2)  # 打开浏览器
                webbrowser.open_new_tab(f"http://localhost:{PORT}/?__theme=dark")

            threading.Thread(target=open, name="open-browser", daemon=True).start()
            threading.Thread(target=auto_update, name="self-upgrade", daemon=True).start()
        # threading.Thread(target=warm_up_modules, name="warm-up", daemon=True).start()

    def main(self):
        with gr.Blocks(title="Chatbot for KSO ", theme=set_theme, analytics_enabled=False, css=custom_css) as self.demo:
            # 绘制页面title
            self.draw_title()
            # 绘制一个ROW，row会让底下的元素自动排成一行
            with gr.Row().style(justify='between'):
                # 绘制列1
                with gr.Column(scale=40, elem_id='colum_1') as self.cloum_1:
                    gr.Markdown('# KSO Chat Bot 🦾')
                    with gr.Tabs() as self.tabs_funcs:
                        self.draw_function_chat()
                        self.draw_plugin_chat()
                        self.draw_langchain_base()
                        self.draw_setting_chat()
                # 绘制列2
                with gr.Column(scale=100):
                    with gr.Tabs() as self.tabs_chatbot:
                        with gr.TabItem('Chatbot', id='chatbot') as self.chat_tab:
                            self.draw_chatbot()
                            self.draw_examples()
                        with gr.TabItem('提示词、对话记录搜索') as self.prompt_tab:
                            self.draw_prompt()

            # 函数注册，需要在Blocks下进行
            self.signals_input_setting()
            self.signals_sm_btn()
            self.signals_prompt_func()
            self.signals_prompt_edit()
            self.signals_plugin()
            self.signals_langchain_cn()
            adv_plugins = gr.State([i for i in crazy_fns])
            self.demo.load(fn=func_box.refresh_load_data,
                           inputs=[self.chatbot, self.history, self.pro_fp_state, adv_plugins],
                           outputs=[self.pro_func_prompt, self.pro_fp_state, self.chatbot,
                                    self.history, self.guidance_plugins, self.guidance_plugins_state,
                                    self.cloum_1, self.examples_column, self.langchain_dropdown, self.langchain_select])

        # Start
        self.auto_opentab_delay()
        self.demo.queue(concurrency_count=CONCURRENT_COUNT,).launch(server_name="0.0.0.0", server_port=PORT, auth=AUTHENTICATION,
        blocked_paths=["config.py", "config_private.py", "docker-compose.yml", "Dockerfile"], show_api=False)


def check_proxy_free():
    proxy_state = func_box.Shell(f'lsof -i :{PORT}').read()[1].splitlines()
    if proxy_state != ["", ""]:
        print('Kill Old Server')
        for i in proxy_state[1:]:
            func_box.Shell(f'kill -9 {i.split()[1]}').read()
        import time
        time.sleep(5)


if __name__ == '__main__':
    # PORT = find_free_port() if WEB_PORT <= 0 else WEB_PORT
    PORT = LOCAL_PORT if WEB_PORT <= 0 else WEB_PORT
    check_proxy_free()
    reload_javascript()
    chatbot_main = ChatBot()
    chatbot_main.main()
    gr.close_all()
    check_proxy_free()

