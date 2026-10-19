import { useState } from "react";
import { Keyboard, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { StatusBar } from "expo-status-bar";

type Todo = { id: number; title: string; done: boolean };

export default function App() {
  const [draft, setDraft] = useState("");
  const [todos, setTodos] = useState<Todo[]>([]);
  const [nextId, setNextId] = useState(1);
  const title = draft.trim();
  const isEmpty = title.length === 0;
  const completed = todos.filter((todo) => todo.done).length;

  function addTodo() {
    if (isEmpty) return;
    setTodos((current) => [...current, { id: nextId, title, done: false }]);
    setNextId((current) => current + 1);
    setDraft("");
    Keyboard.dismiss();
  }

  function resetTodos() {
    setTodos([]);
    setDraft("");
    setNextId(1);
    Keyboard.dismiss();
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <StatusBar style="dark" />
      <Text style={styles.eyebrow}>EXPO × ARTEMIS</Text>
      <Text accessibilityRole="header" style={styles.heading}>
        Artemis Todo
      </Text>
      <Text style={styles.subtitle}>小さな操作から、自動テストを試そう。</Text>
      <View style={styles.card}>
        <Text style={styles.label}>新しいタスク</Text>
        <TextInput
          accessibilityLabel="タスク名"
          testID="todo-input"
          style={styles.input}
          placeholder="例: 牛乳を買う"
          value={draft}
          onChangeText={setDraft}
          onSubmitEditing={addTodo}
          returnKeyType="done"
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="追加"
          accessibilityState={{ disabled: isEmpty }}
          disabled={isEmpty}
          onPress={addTodo}
          style={[styles.button, isEmpty ? styles.disabled : null]}
        >
          <Text style={styles.buttonText}>追加</Text>
        </Pressable>
      </View>
      <Text accessibilityLiveRegion="polite" testID="todo-summary" style={styles.label}>
        {`タスク ${todos.length}件 / 完了 ${completed}件`}
      </Text>
      {todos.length === 0 ? <Text style={styles.subtitle}>タスクはありません</Text> : null}
      {todos.map((todo) => (
        <Pressable
          key={todo.id}
          accessibilityRole="checkbox"
          accessibilityLabel={todo.title}
          accessibilityState={{ checked: todo.done }}
          onPress={() =>
            setTodos((current) =>
              current.map((item) => (item.id === todo.id ? { ...item, done: !item.done } : item)),
            )
          }
          style={styles.card}
        >
          <View style={styles.taskTitle}>
            <Text style={styles.checkbox} importantForAccessibility="no">
              {todo.done ? "☑" : "☐"}
            </Text>
            <Text style={todo.done ? styles.done : styles.label}>{todo.title}</Text>
          </View>
          <Text style={styles.subtitle}>{todo.done ? "完了" : "未完了"}</Text>
        </Pressable>
      ))}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="すべてリセット"
        onPress={resetTodos}
        style={styles.reset}
      >
        <Text style={styles.resetText}>すべてリセット</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    flexGrow: 1,
    backgroundColor: "#f4f6fa",
    padding: 24,
    paddingTop: 72,
    paddingBottom: 48,
    gap: 20,
  },
  eyebrow: { color: "#3554b5", fontWeight: "700", letterSpacing: 2 },
  heading: { fontSize: 32, fontWeight: "800", color: "#142348" },
  subtitle: { color: "#596579", fontSize: 16 },
  label: { color: "#142348", fontSize: 16, fontWeight: "600" },
  card: {
    backgroundColor: "#fff",
    padding: 20,
    borderRadius: 18,
    borderCurve: "continuous",
    gap: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: "#bbc6da",
    borderRadius: 10,
    borderCurve: "continuous",
    padding: 14,
    fontSize: 16,
    color: "#142348",
  },
  button: {
    backgroundColor: "#3554b5",
    borderRadius: 10,
    borderCurve: "continuous",
    padding: 16,
    alignItems: "center",
  },
  disabled: { opacity: 0.4 },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  done: { color: "#596579", textDecorationLine: "line-through", fontSize: 16 },
  taskTitle: { flexDirection: "row", alignItems: "center", gap: 12 },
  checkbox: { fontSize: 28, color: "#3554b5" },
  reset: { padding: 16, alignItems: "center" },
  resetText: { color: "#3554b5", fontSize: 16, fontWeight: "600" },
});
