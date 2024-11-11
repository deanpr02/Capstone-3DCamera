# Makefile adapted from https://makefiletutorial.com/

.PHONY: all clean run-sender run-receiver

sender_DIR := ./sender
receiver_DIR := ./receiver
util_DIR := ./util

SRC_DIR := src
OBJ_DIR := obj
BIN_DIR := bin

# Find all the C++ files we want to compile
# Note the single quotes around the * expressions. The shell will incorrectly expand these otherwise, but we want to send the * directly to the find command.
sender_SRCS := $(shell find $(sender_DIR)/$(SRC_DIR) -name '*.cpp')
receiver_SRCS := $(shell find $(receiver_DIR)/$(SRC_DIR) -name '*.cpp')
util_SRCS := $(shell find $(util_DIR)/$(SRC_DIR) -name '*.cpp')

# Replace SRC_DIR with OBJ_DIR and append .o
sender_OBJS := $(patsubst $(sender_DIR)/$(SRC_DIR)/%.cpp, $(sender_DIR)/$(OBJ_DIR)/%.cpp.o, $(sender_SRCS))
receiver_OBJS := $(patsubst $(receiver_DIR)/$(SRC_DIR)/%.cpp, $(receiver_DIR)/$(OBJ_DIR)/%.cpp.o, $(receiver_SRCS))
util_OBJS := $(patsubst $(util_DIR)/$(SRC_DIR)/%.cpp, $(util_DIR)/$(OBJ_DIR)/%.cpp.o, $(util_SRCS))

# String substitution (suffix version without %).
# As an example, ./build/hello.cpp.o turns into ./build/hello.cpp.d
sender_DEPS := $(sender_OBJS:.o=.d)
receiver_DEPS := $(receiver_OBJS:.o=.d)
util_DEPS := $(util_OBJS:.o=.d)

# Every folder in ./src will need to be passed to GCC so that it can find header files
sender_INC_DIRS := $(shell find $(sender_DIR)/$(SRC_DIR) -type d)
receiver_INC_DIRS := $(shell find $(receiver_DIR)/$(SRC_DIR) -type d)
util_INC_DIRS := $(shell find $(util_DIR)/$(SRC_DIR) -type d)
# Add a prefix to INC_DIRS. So moduleA would become -ImoduleA. GCC understands this -I flag
util_INC_FLAGS := $(addprefix -I,$(util_INC_DIRS))
sender_INC_FLAGS := $(util_INC_FLAGS) $(addprefix -I,$(sender_INC_DIRS))
receiver_INC_FLAGS := $(util_INC_FLAGS) $(addprefix -I,$(receiver_INC_DIRS))

# The -MMD and -MP flags together generate Makefiles for us!
# These files will have .d instead of .o as the output.
CPPFLAGS := -g -MMD -MP -std=c++20 -Wall -Wreturn-type -I/opt/homebrew/include
LDFLAGS := -L/opt/homebrew/lib -lsrt
CXX := g++

all: sender receiver

sender: $(BIN_DIR)/sender
receiver: $(BIN_DIR)/receiver

$(BIN_DIR)/sender: $(sender_OBJS) $(util_OBJS)
	mkdir -p $(dir $@)
	$(CXX) $(sender_OBJS) $(util_OBJS) -o $@ $(LDFLAGS)

$(BIN_DIR)/receiver: $(receiver_OBJS) $(util_OBJS)
	mkdir -p $(dir $@)
	$(CXX) $(receiver_OBJS) $(util_OBJS) -o $@ $(LDFLAGS)

# Build step for C++ source
$(sender_DIR)/$(OBJ_DIR)/%.cpp.o: $(sender_DIR)/$(SRC_DIR)/%.cpp
	mkdir -p $(dir $@)
	$(CXX) $(sender_INC_FLAGS) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(receiver_DIR)/$(OBJ_DIR)/%.cpp.o: $(receiver_DIR)/$(SRC_DIR)/%.cpp
	mkdir -p $(dir $@)
	$(CXX) $(receiver_INC_FLAGS) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(util_DIR)/$(OBJ_DIR)/%.cpp.o: $(util_DIR)/$(SRC_DIR)/%.cpp
	mkdir -p $(dir $@)
	$(CXX) $(util_INC_FLAGS) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

clean:
	rm -r $(BIN_DIR)
	rm -r $(sender_DIR)/$(OBJ_DIR)
	rm -r $(receiver_DIR)/$(OBJ_DIR)
	rm -r $(util_DIR)/$(OBJ_DIR)

run-sender: sender
	$(BIN_DIR)/sender

run-receiver: receiver
	$(BIN_DIR)/receiver

# Include the .d makefiles. The - at the front suppresses the errors of missing
# Makefiles. Initially, all the .d files will be missing, and we don't want those
# errors to show up.
-include $(sender_DEPS)
-include $(receiver_DEPS)
-include $(util_DEPS)