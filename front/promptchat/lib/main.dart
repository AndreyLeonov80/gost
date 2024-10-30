
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'ИИ для ГОСТ 14637-89',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const ChatPage(),
    );
  }
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  _ChatPageState createState() => _ChatPageState();
}

class QuestionAnswer {
  final String question;
  final String answer;
  final String sourceFile;

  QuestionAnswer({
    required this.question,
    required this.answer,
    required this.sourceFile,
  });

  factory QuestionAnswer.fromJson(Map<String, dynamic> json, String fileName) {
    return QuestionAnswer(
      question: json['q'] as String,
      answer: json['a'] as String,
      sourceFile: fileName,
    );
  }
}

class Message {
  final String text;
  final bool isFromAI;

  Message(this.text, this.isFromAI);
}

class _ChatPageState extends State<ChatPage> {
  List<QuestionAnswer> _qaList = [];
  late TextEditingController _controller;
  final List<Message> _messages = [];
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();
  List<QuestionAnswer> _currentSuggestions = [];
  bool _showSuggestions = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
    loadJsonData();

    _controller.addListener(() {
      _updateSuggestions();
    });
  }

  Future<void> loadJsonData() async {
    try {
      List<QuestionAnswer> allData = [];

      final manifestContent = await rootBundle.loadString('AssetManifest.json');
      final Map<String, dynamic> manifestMap = json.decode(manifestContent);

      final jsonPaths = manifestMap.keys
          .where((String key) => key.startsWith('assets/') && key.endsWith('.json'))
          .toList();

      for (String path in jsonPaths) {
        try {
          String jsonString = await rootBundle.loadString(path);

          final List<dynamic> jsonResponse = json.decode(jsonString);

          for (var item in jsonResponse) {
            if (item is! Map<String, dynamic> ||
                !item.containsKey('q') ||
                !item.containsKey('a')) {
              throw FormatException(
                  'Неверная структура JSON в файле $path. Каждый объект должен содержать поля "q" и "a"'
              );
            }
          }

          String fileName = path.split('/').last;

          allData.addAll(
              jsonResponse.map((item) => QuestionAnswer.fromJson(item, fileName)).toList()
          );

          debugPrint('Успешно загружен файл: $path');
        } catch (e) {
          debugPrint('Ошибка при загрузке файла $path: $e');
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Ошибка в файле ${path.split('/').last}: $e'),
                backgroundColor: Colors.red,
              ),
            );
          }
        }
      }

      setState(() {
        _qaList = allData;
      });

      if (allData.isEmpty) {
        throw Exception('Не удалось загрузить данные ни из одного файла');
      }

    } catch (e) {
      debugPrint('Общая ошибка загрузки JSON: $e');
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Ошибка загрузки данных: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _updateSuggestions() {
    if (_controller.text.isEmpty) {
      setState(() {
        _currentSuggestions = [];
        _showSuggestions = false;
      });
      return;
    }

    final String currentWord = _getCurrentWord();
    if (currentWord.isEmpty) {
      setState(() {
        _currentSuggestions = [];
        _showSuggestions = false;
      });
      return;
    }

    final suggestions = _qaList.where((qa) =>
        qa.question.toLowerCase().contains(currentWord.toLowerCase())
    ).take(5).toList();

    setState(() {
      _currentSuggestions = suggestions;
      _showSuggestions = suggestions.isNotEmpty;
    });
  }

  String _getCurrentWord() {
    final text = _controller.text;
    final selection = _controller.selection;
    if (selection.start < 0) return '';

    final beforeCursor = text.substring(0, selection.start);
    final words = beforeCursor.split(' ');
    return words.last;
  }

  void _insertSuggestion(QuestionAnswer qa) {
    final text = _controller.text;
    final selection = _controller.selection;
    final beforeCursor = text.substring(0, selection.start);
    final afterCursor = text.substring(selection.start);

    final words = beforeCursor.split(' ');
    words.removeLast();
    words.add(qa.question);

    final newText = '${words.join(' ')} $afterCursor';

    setState(() {
      _controller.text = newText;
      _controller.selection = TextSelection.collapsed(
        offset: words.join(' ').length + 1,
      );
      _showSuggestions = false;
    });

    _sendMessage(qa.question);
    _addAIResponse(qa.answer);

    _focusNode.requestFocus();
  }

  void _sendMessage(String message) {
    if (message.trim().isEmpty) return;

    setState(() {
      _messages.add(Message(message.trim(), false));
      _controller.clear();
      _showSuggestions = false;
    });

    _scrollToBottom();
  }

  void _addAIResponse(String response) {
    setState(() {
      _messages.add(Message(response, true));
    });

    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ИИ для ГОСТ 14637-89'),
        elevation: 2,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: _buildMessagesList(),
            ),
            _buildSuggestionsArea(),
            _buildInputArea(),
          ],
        ),
      ),
    );
  }

  Widget _buildMessagesList() {
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(8),
      itemCount: _messages.length,
      itemBuilder: (context, index) {
        final message = _messages[index];
        return Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: message.isFromAI ? Colors.green.shade100 : Colors.blue.shade100,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                offset: const Offset(0, 1),
                blurRadius: 2,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                message.isFromAI ? 'ИИ:' : 'Вы:',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: message.isFromAI ? Colors.green.shade900 : Colors.blue.shade900,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                message.text,
                style: const TextStyle(fontSize: 16),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSuggestionsArea() {
    if (!_showSuggestions || _currentSuggestions.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      constraints: const BoxConstraints(maxHeight: 300),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          top: BorderSide(color: Colors.grey.shade300),
        ),
      ),
      child: ListView.builder(
        shrinkWrap: true,
        itemCount: _currentSuggestions.length,
        itemBuilder: (context, index) {
          final qa = _currentSuggestions[index];
          return Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(color: Colors.grey.shade200),
              ),
            ),
            child: InkWell(
              onTap: () => _insertSuggestion(qa),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          qa.question,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.blue.shade100,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          qa.sourceFile,
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.blue.shade900,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    qa.answer,
                    style: TextStyle(
                      color: Colors.grey.shade700,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            offset: const Offset(0, -1),
            blurRadius: 2,
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              decoration: InputDecoration(
                hintText: 'Введите сообщение',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
              ),
              onSubmitted: _sendMessage,
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.send),
            onPressed: () => _sendMessage(_controller.text),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }
}
