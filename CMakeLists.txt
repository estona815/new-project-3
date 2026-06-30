cmake_minimum_required(VERSION 3.16)

project(MasteringQAAnalyzer VERSION 0.1.0 LANGUAGES CXX)

add_library(mastering_qa_analyzer
    analyzer/AnalysisResult.cpp
    analyzer/AudioFileLoader.cpp
    analyzer/JsonReportWriter.cpp
    analyzer/LoudnessAnalyzer.cpp
    analyzer/PhaseAnalyzer.cpp
    analyzer/STFTAnalyzer.cpp
    analyzer/TextureAnalyzer.cpp
    analyzer/TransientAnalyzer.cpp
)

target_include_directories(mastering_qa_analyzer
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/analyzer
        ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_features(mastering_qa_analyzer PUBLIC cxx_std_17)

add_executable(test_mastering_qa_analyzer
    tests/test_mastering_qa_analyzer.cpp
)

target_link_libraries(test_mastering_qa_analyzer
    PRIVATE
        mastering_qa_analyzer
)

enable_testing()
add_test(NAME mastering_qa_analyzer COMMAND test_mastering_qa_analyzer)
